"""Google Gemini provider: turns the transcript into storybook text, server-side only.

Only transcript TEXT is sent, never audio. The API key stays on the server (it is read from the
environment, never sent to the browser, and never included in error messages).
The drafts are suggestions: every new or changed sentence enters the book as "needs review".
"""
import json
import time

import httpx

from ..schemas import StoryProject
from .base import ProviderError, Revision, StoryDraft

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TEMPORARY_STATUSES = {429, 500, 502, 503, 504}  # worth trying again; 400/403/404 are not
RETRY_WAITS = (2, 6)  # seconds to wait before the 2nd and 3rd try

PRONOUN_FORMS = {  # subject, object, possessive
    "she/her": ("she", "her", "her"),
    "he/him": ("he", "him", "his"),
    "they/them": ("they", "them", "their"),
}


def system_instruction(name: str, pronouns: str) -> str:
    subject, _object, possessive = PRONOUN_FORMS[pronouns]
    return f"""You are a gentle picture-book writer helping a family turn an older person's spoken memories into a short, beautiful picture book. The family will review every sentence before the book is printed or shared.

In the book the storyteller is called "{name}". Use {pronouns} pronouns for {name}.

You are given numbered transcript lines: what {name} said, written down by a computer, so it can contain mistakes.

Write:
- book_title: a warm, fun title for the book, at most 8 words, using the name "{name}" and the main theme of the memories (for example "Gram's Typical Day in High School").
- pages: the story split into picture-book pages, in the order things happened. Each page has 1 to 3 short sentences (at most about 45 words in total) and a photo_idea: one short phrase describing a picture for that page, using only things {name} mentioned (for example "a blue bike with a basket"). Usually 6 to 12 pages.

How to write the story:
1. Tell it as a story ABOUT {name}, in the third person ("Every morning, {name} hopped on {possessive} bike..."). Do not list facts, do not quote the transcript, and do not write "{name} said" or "{name} remembered" unless it truly helps the story.
2. Use a warm, flowing picture-book voice: vary sentence length, use simple storytelling transitions ("Every morning", "Then", "Years later"), and keep {name}'s own memorable words and phrases where you can. When {subject} said how something felt, bring that feeling out; never invent feelings {subject} did not express.
3. NO NEW FACTS. Every fact must come from the transcript lines. Never add names, places, numbers, dates, people, objects, events, weather, sounds, or reasons that were not said. Never change a number, a name, a date, or whether something happened or did not happen. Storytelling words that add no new fact are fine; invented details are not.
4. Leave out filler words, false starts, repeats, and anything unclear or garbled. If you are not sure what was meant, leave it out instead of guessing.
5. Every sentence must list the ids of the transcript lines it is based on (source_segment_ids).
6. Leave out health details, street addresses, phone numbers, financial details, and private information about other people, even if they appear in the lines.
Return only JSON that matches the requested schema."""


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "book_title": {"type": "STRING"},
        "pages": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "photo_idea": {"type": "STRING"},
                    "sentences": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "text": {"type": "STRING"},
                                "source_segment_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
                            },
                            "required": ["text", "source_segment_ids"],
                        },
                    },
                },
                "required": ["photo_idea", "sentences"],
            },
        },
    },
    "required": ["book_title", "pages"],
}


def build_user_prompt(project: StoryProject) -> str:
    """Every transcript line, numbered, in order."""
    return "\n".join(f"[{segment.id}] {segment.text}" for segment in project.transcript)


def revision_instruction(name: str, pronouns: str) -> str:
    _subject, _object, possessive = PRONOUN_FORMS[pronouns]
    return f"""You are helping a family finish a short picture book about {name}, written from a recording of {name} telling {possessive} own memories. Use {pronouns} pronouns for {name}.

A family member or volunteer has read the book and is asking for a change. You are given the transcript lines (what {name} said, written down by a computer, so it can contain mistakes), the book as it is now, and their request.

Return the WHOLE book with the request carried out:
1. Change only what the request asks for. Copy every other page and sentence exactly, word for word, with the same source_segment_ids.
2. Keep the pages in the same order. Add, remove, split, merge, or move pages only if the request asks for it.
3. For every page, from_page is the id of the current page it comes from (for example "p3"), or "new" for a page that did not exist before.
4. Keep book_title exactly as it is unless the request is about the title.
5. The person asking knows {name}, so you may use facts that are in their request. A sentence based only on the request has an empty source_segment_ids list. Every other sentence lists the transcript lines it is based on.
6. Otherwise add NO NEW FACTS: no names, places, numbers, dates, people, objects, events, or feelings that are not in the transcript or in the request.
7. Keep the picture-book style: a story about {name} in the third person, warm and simple, 1 to 3 short sentences per page (about 45 words at most).
8. Leave out health details, street addresses, phone numbers, financial details, and private information about other people, even if the request includes them.
9. reply: one or two short, friendly sentences telling the person what you changed and on which pages (the cover is page 1, so the story starts on page 2). If the request is unclear, or would need facts you do not have, change nothing and use reply to ask a short question instead.
Return only JSON that matches the requested schema."""


REVISION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "reply": {"type": "STRING"},
        "book_title": {"type": "STRING"},
        "pages": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "from_page": {"type": "STRING"},
                    **RESPONSE_SCHEMA["properties"]["pages"]["items"]["properties"],
                },
                "required": ["from_page", "photo_idea", "sentences"],
            },
        },
    },
    "required": ["reply", "book_title", "pages"],
}


def build_revision_prompt(project: StoryProject, request: str) -> str:
    """The transcript, the book as it is now (pages numbered as the reviewer sees them), and the request."""
    from ..services.book_pdf import book_title_for  # imported here: drafting a new story does not need it

    book = {
        "book_title": book_title_for(project),
        "pages": [
            {
                "page": number,
                "id": chapter.id,
                "photo_idea": chapter.photo_idea or "",
                "sentences": [
                    {"text": s.text, "source_segment_ids": s.source_segment_ids}
                    for s in chapter.sentences if s.status != "removed"
                ],
            }
            for number, chapter in enumerate(project.chapters, start=2)  # page 1 is the cover
        ],
    }
    return (
        "Transcript lines:\n" + build_user_prompt(project)
        + "\n\nThe book now (page 1 is the cover, so the story starts on page 2):\n"
        + json.dumps(book, ensure_ascii=False, indent=1)
        + "\n\nThe request from the person reviewing the book:\n<request>\n" + request + "\n</request>"
    )


class GeminiProvider:
    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None, sleep=time.sleep):
        self._api_key = api_key
        self.model = model
        self.name = f"Google Gemini ({model})"
        # a hung service must not stall the demo for long: after this the saved draft is used instead
        self._client = client or httpx.Client(timeout=httpx.Timeout(75, connect=10))
        self._sleep = sleep

    def draft_story(self, project: StoryProject) -> StoryDraft:
        if not project.family_name or not project.pronouns:
            raise ValueError("The family name and pronouns are needed to write the story.")
        system = system_instruction(project.family_name, project.pronouns)
        return self._generate(system, build_user_prompt(project), RESPONSE_SCHEMA, 0.6, StoryDraft)

    def revise_story(self, project: StoryProject, request: str) -> Revision:
        """The whole book again, with the reviewer's request carried out."""
        if not project.family_name or not project.pronouns:
            raise ValueError("The family name and pronouns are needed to change the story.")
        system = revision_instruction(project.family_name, project.pronouns)
        return self._generate(system, build_revision_prompt(project, request), REVISION_SCHEMA, 0.3, Revision)

    def _generate(self, system: str, prompt: str, schema: dict, temperature: float, model):
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "maxOutputTokens": 16384,
            },
        }
        for wait in (*RETRY_WAITS, None):
            try:
                response = self._client.post(
                    ENDPOINT.format(model=self.model), headers={"x-goog-api-key": self._api_key}, json=body
                )
            except httpx.HTTPError as error:
                raise ProviderError("Could not reach Google's AI service. Check the internet connection.") from error
            if response.status_code == 200:
                return _parse_answer(response, model)
            if response.status_code not in TEMPORARY_STATUSES or wait is None:
                break
            self._sleep(wait)
        raise ProviderError(f"Google's AI service said no ({response.status_code}): {_error_message(response)}")


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])[:200]
    except Exception:
        return "no details"


def _parse_answer(response: httpx.Response, model=StoryDraft):
    try:
        candidate = response.json()["candidates"][0]
        if candidate.get("finishReason") not in (None, "STOP"):
            raise ProviderError(f"Google's answer was cut off or blocked ({candidate.get('finishReason')}).")
        text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
        return model.model_validate(json.loads(text))
    except ProviderError:
        raise
    except Exception as error:
        raise ProviderError("Google's answer was not in the form StoryBridge expects.") from error
