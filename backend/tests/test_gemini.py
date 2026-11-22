import json

import httpx
import pytest

from app.providers.base import ProviderError
from app.providers.gemini import ENDPOINT, GeminiProvider, build_user_prompt, system_instruction
from test_drafting import project_with_transcript

SECRET = "AQ.test-secret-key-123"


def provider_with(handler, waits=None) -> GeminiProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GeminiProvider(SECRET, "gemini-test", client=client, sleep=(waits.append if waits is not None else lambda s: None))


def named_project():
    project = project_with_transcript()
    project.family_name, project.pronouns = "Gram", "she/her"
    return project


def answer(pages, finish="STOP", title="Gram's Typical Day"):
    text = json.dumps({"book_title": title, "pages": pages})
    return {"candidates": [{"finishReason": finish, "content": {"parts": [{"text": text}]}}]}


GOOD = [{"photo_idea": "a red bike", "sentences": [{"text": "Gram rode off.", "source_segment_ids": ["seg-0001"]}]}]


def test_prompt_lists_every_line_in_order():
    prompt = build_user_prompt(project_with_transcript(3))
    assert prompt == "[seg-0001] Line 1.\n[seg-0002] Line 2.\n[seg-0003] Line 3."


def test_instructions_ask_for_picture_book_pages_about_them_with_no_new_facts():
    text = system_instruction("Gram", "she/her")
    for phrase in ['called "Gram"', "she/her pronouns", "third person", "Gram hopped on her bike", "NO NEW FACTS",
                   "Never add names", "Never change a number", "source_segment_ids", "book_title", "photo_idea",
                   "picture-book pages", "1 to 3 short sentences", "never invent feelings", "Leave out health details"]:
        assert phrase in text, phrase


@pytest.mark.parametrize("pronouns, possessive", [("he/him", "his"), ("they/them", "their")])
def test_instructions_use_the_chosen_pronouns(pronouns, possessive):
    assert f"Pop hopped on {possessive} bike" in system_instruction("Pop", pronouns)


def test_name_and_pronouns_are_required():
    with pytest.raises(ValueError):
        provider_with(lambda r: httpx.Response(200, json=answer(GOOD))).draft_story(project_with_transcript())


def test_request_shape_and_where_the_key_goes():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["headers"], seen["body"] = str(request.url), request.headers, json.loads(request.content)
        return httpx.Response(200, json=answer(GOOD))

    story = provider_with(handler).draft_story(named_project())
    assert seen["url"] == ENDPOINT.format(model="gemini-test")
    assert seen["headers"]["x-goog-api-key"] == SECRET and SECRET not in seen["url"]
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert 'called "Gram"' in seen["body"]["systemInstruction"]["parts"][0]["text"]
    assert "[seg-0001] Line 1." in seen["body"]["contents"][0]["parts"][0]["text"]
    assert story.book_title == "Gram's Typical Day"
    assert story.pages[0].photo_idea == "a red bike" and story.pages[0].sentences[0].text == "Gram rode off."


def test_only_transcript_text_is_sent_never_audio():
    seen = {}

    def handler(request):
        seen["raw"] = request.content
        return httpx.Response(200, json=answer(GOOD))

    provider_with(handler).draft_story(named_project())
    assert b"inlineData" not in seen["raw"] and b"fileData" not in seen["raw"]


def test_temporary_errors_are_retried_then_succeed():
    statuses = iter([503, 429])
    waits = []

    def handler(request):
        status = next(statuses, 200)
        return httpx.Response(status, json={"error": {"message": "busy"}} if status != 200 else answer(GOOD))

    story = provider_with(handler, waits).draft_story(named_project())
    assert story.pages[0].photo_idea == "a red bike" and waits == [2, 6]


def test_temporary_errors_give_up_after_three_tries():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, json={"error": {"message": "high demand"}})

    with pytest.raises(ProviderError, match="503"):
        provider_with(handler).draft_story(named_project())
    assert len(calls) == 3


@pytest.mark.parametrize("status", [400, 403, 404])
def test_permanent_errors_are_not_retried(status):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(status, json={"error": {"message": "no"}})

    with pytest.raises(ProviderError):
        provider_with(handler).draft_story(named_project())
    assert len(calls) == 1


@pytest.mark.parametrize("status", [400, 403, 429, 500])
def test_http_errors_become_provider_errors_without_leaking_the_key(status):
    def handler(request):
        return httpx.Response(status, json={"error": {"message": "nope, try later"}})

    with pytest.raises(ProviderError) as error:
        provider_with(handler).draft_story(named_project())
    assert str(status) in str(error.value) and "nope, try later" in str(error.value)
    assert SECRET not in str(error.value)


def test_network_failure_is_a_provider_error():
    def handler(request):
        raise httpx.ConnectError("no internet")

    with pytest.raises(ProviderError, match="Could not reach"):
        provider_with(handler).draft_story(named_project())


@pytest.mark.parametrize("finish", ["MAX_TOKENS", "SAFETY"])
def test_a_cut_off_or_blocked_answer_is_a_provider_error(finish):
    def handler(request):
        return httpx.Response(200, json=answer(GOOD, finish=finish))

    with pytest.raises(ProviderError, match="cut off or blocked"):
        provider_with(handler).draft_story(named_project())


@pytest.mark.parametrize(
    "body",
    [
        {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "not json at all"}]}}]},
        {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"nope": []}'}]}}]},
        {"candidates": []},
        {},
    ],
)
def test_an_unusable_answer_is_a_provider_error(body):
    def handler(request):
        return httpx.Response(200, json=body)

    with pytest.raises(ProviderError, match="not in the form"):
        provider_with(handler).draft_story(named_project())


# --- asking for changes ------------------------------------------------------------------------------

def test_a_change_request_sends_the_book_and_the_request_and_reads_the_reply():
    from test_drafting import page, pages_from_draft, story

    project = named_project()
    project.chapters = pages_from_draft(project, story(page("seg-0001", text="Gram biked to school."), page("seg-0002")))
    project.chapters[0].sentences.append(project.chapters[1].sentences[0].model_copy(
        update={"id": "p1-s2", "text": "A sentence a person removed.", "status": "removed"}))
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        revised = {"reply": "I changed page 2.", "book_title": "Gram's Day", "pages": [
            {"from_page": "p1", "photo_idea": "a red bike", "sentences": [{"text": "Gram rode.", "source_segment_ids": []}]}]}
        return httpx.Response(200, json={"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(revised)}]}}]})

    revision = provider_with(handler).revise_story(project, "Her bike was red.")
    prompt = seen["body"]["contents"][0]["parts"][0]["text"]
    assert "[seg-0001] Line 1." in prompt  # the transcript
    assert '"page": 2' in prompt and '"id": "p1"' in prompt and "Gram biked to school." in prompt  # the book as the reviewer sees it
    assert "A sentence a person removed." not in prompt
    assert prompt.rstrip().endswith("<request>\nHer bike was red.\n</request>")
    assert "from_page" in seen["body"]["generationConfig"]["responseSchema"]["properties"]["pages"]["items"]["required"]
    assert "Change only what the request asks for" in seen["body"]["systemInstruction"]["parts"][0]["text"]
    assert b"inlineData" not in json.dumps(seen["body"]).encode()
    assert revision.reply == "I changed page 2." and revision.pages[0].from_page == "p1"
