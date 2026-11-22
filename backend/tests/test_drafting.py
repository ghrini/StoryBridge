import json

import pytest

from app.config import Settings
from app.providers.base import DraftSentence, PageDraft, ProviderError, StoryDraft
from app.providers.fixture import FixtureProvider
from app.schemas import StoryProject, TranscriptSegment
from app.services.drafting import (
    AI_WARNING,
    SYNTHETIC_FIXTURE,
    DraftError,
    SentenceNotFound,
    apply_drafts,
    draft_story,
    external_ai_block_reason,
    own_words_pages,
    pages_from_draft,
    saved_provider,
    transcript_fingerprint,
    update_sentence,
)
from app.services.storage import ProjectStore
from test_schemas import make_consent


def make_settings(tmp_path, **overrides) -> Settings:
    fields = dict(
        data_dir=tmp_path, models_dir=tmp_path / "models", ffmpeg="ffmpeg", whisper_model="small",
        base_url="http://localhost:8000", clip_padding_seconds=0.25,
    )
    fields.update(overrides)
    return Settings(**fields)


def transcript(count=22):
    return [TranscriptSegment(id=f"seg-{i + 1:04d}", text=f"Line {i + 1}.", start=i * 2.0, end=i * 2.0 + 1.5)
            for i in range(count)]


def project_with_transcript(count=22, kind="synthetic_dev") -> StoryProject:
    return StoryProject(id="abcd1234", recording_kind=kind, transcript=transcript(count))


def page(*sources, text="A drafted sentence.", idea=None) -> PageDraft:
    return PageDraft(photo_idea=idea, sentences=[DraftSentence(text=text, source_segment_ids=list(sources or ("seg-0001",)))])


def story(*pages, title=None) -> StoryDraft:
    return StoryDraft(book_title=title, pages=list(pages))


def three_pages(title=None) -> StoryDraft:
    return story(page("seg-0001"), page("seg-0009"), page("seg-0017"), title=title)


class FakeLive:
    """Stands in for the Gemini provider: returns scripted answers or raises ProviderError."""

    name = "Fake AI"

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = 0

    def draft_story(self, project):
        self.calls += 1
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def stored_project(tmp_path, kind="synthetic_dev", named=True, count=22, consent=None):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind=kind, consent=consent)
    project.transcript = transcript(count)
    if named:
        project.family_name, project.pronouns = "Gram", "she/her"
    return store, project


def save_draft(store, project, draft: StoryDraft, **extra):
    data = {**draft.model_dump(mode="json"), **extra}
    (store.project_dir(project.id) / "ai_draft.json").write_text(json.dumps(data), encoding="utf-8")


# --- turning a draft into pages -------------------------------------------------------------------

def test_a_draft_becomes_pages_that_need_review():
    project = project_with_transcript()
    pages = pages_from_draft(project, story(page("seg-0003", "seg-0001", idea=" a blue bike "), page("seg-0009")))
    assert [p.id for p in pages] == ["p1", "p2"]
    first = pages[0]
    assert first.segment_ids == ["seg-0001", "seg-0003"]  # in recording order
    assert (first.clip_start, first.clip_end) == (0.0, 5.5)  # from the first to the last cited line
    assert first.photo_idea == "a blue bike"
    [sentence] = first.sentences
    assert (sentence.id, sentence.edit_type, sentence.status, sentence.grounding_score) == ("p1-s1", "ai_draft", "flagged", None)


def test_empty_pages_are_skipped_and_numbering_stays_in_order():
    project = project_with_transcript()
    pages = pages_from_draft(project, story(page("seg-0001"), page("seg-0002", text="   "), page("seg-0003")))
    assert [p.id for p in pages] == ["p1", "p2"]


@pytest.mark.parametrize("bad", [
    story(page("seg-9999")),                                          # a line that isn't in the recording
    story(PageDraft(sentences=[DraftSentence(text="Hi.", source_segment_ids=[])])),  # no source at all
    story(page("seg-0001", text="  ")),                               # no words left
    story(),                                                          # no pages
])
def test_a_bad_draft_is_rejected_and_changes_nothing(bad):
    project = project_with_transcript()
    before = project.model_dump()
    with pytest.raises(DraftError):
        apply_drafts(project, bad, "p")
    assert project.model_dump() == before


def test_older_chapter_drafts_are_read_as_pages():
    old = StoryDraft.model_validate({"book_title": "T", "chapters": [
        {"chapter_id": "ch1", "title": "x", "photo_idea": "bus", "sentences": [{"text": "A.", "source_segment_ids": ["seg-0001"]}]},
        {"chapter_id": "ch2", "sentences": [{"text": "B.", "source_segment_ids": ["seg-0002"]}]}]})
    assert [p.photo_idea for p in old.pages] == ["bus", None] and old.pages[1].sentences[0].text == "B."


def test_own_words_pages_use_the_transcript_a_few_lines_per_page():
    pages = own_words_pages(project_with_transcript(7))
    assert [p.id for p in pages] == ["p1", "p2", "p3"]
    assert [len(p.sentences) for p in pages] == [3, 3, 1]
    assert pages[0].sentences[0].id == "p1-s1" and pages[0].sentences[0].text == "Line 1."
    assert all(s.edit_type == "verbatim" and s.status == "approved" for p in pages for s in p.sentences)


def test_a_draft_brings_a_suggested_title_but_a_persons_title_wins():
    project = project_with_transcript()
    project.book_title = "A title a person typed"
    apply_drafts(project, three_pages(title="Gram's Typical Day"), "p")
    assert project.suggested_title == "Gram's Typical Day" and project.book_title == "A title a person typed"


# --- which saved draft may be used -----------------------------------------------------------------

def test_a_saved_draft_is_only_used_for_the_transcript_it_was_made_from(tmp_path):
    store, project = stored_project(tmp_path)
    save_draft(store, project, three_pages(), transcript_fingerprint="0000000000000000")
    assert saved_provider(store, project) is None
    save_draft(store, project, three_pages(), transcript_fingerprint=transcript_fingerprint(project))
    assert saved_provider(store, project).path.name == "ai_draft.json"
    save_draft(store, project, three_pages())  # saved before fingerprints existed: trusted
    assert saved_provider(store, project) is not None


def test_the_built_in_sample_only_fits_its_own_recording(tmp_path):
    store, project = stored_project(tmp_path)
    assert SYNTHETIC_FIXTURE.is_file()
    assert saved_provider(store, project) is None  # "Line 1." ... is not the "Pop" sample's recording
    assert FixtureProvider(SYNTHETIC_FIXTURE).fingerprint


# --- making the storybook without live AI ------------------------------------------------------------

def test_without_ai_the_book_uses_the_storytellers_own_words(tmp_path):
    store, project = stored_project(tmp_path)
    made = draft_story(store, project, make_settings(tmp_path))
    assert made.drafted_by is None and len(made.chapters) == 8  # 22 lines, 3 per page
    assert all(s.status == "approved" for p in made.chapters for s in p.sentences)
    [warning] = made.warnings
    assert warning.code == AI_WARNING and "own words" in warning.message


def test_a_saved_draft_is_replayed_when_there_is_no_live_ai(tmp_path):
    store, project = stored_project(tmp_path)
    save_draft(store, project, three_pages(title="Saved Title"), drafted_by="Some AI, saved draft")
    made = draft_story(store, project, make_settings(tmp_path))
    assert made.drafted_by == "Some AI, saved draft" and made.suggested_title == "Saved Title"
    assert [p.id for p in made.chapters] == ["p1", "p2", "p3"] and made.warnings == []


def test_the_storybook_needs_a_transcript(tmp_path):
    store, project = stored_project(tmp_path, count=0)
    with pytest.raises(DraftError, match="into text first"):
        draft_story(store, project, make_settings(tmp_path))


# --- live AI: when it may run -------------------------------------------------------------------------

def storyteller(**consent_overrides):
    return StoryProject(id="abcd1234", recording_kind="storyteller", consent=make_consent(**consent_overrides))


def test_no_key_means_no_live_ai(tmp_path):
    assert "No Gemini API key" in external_ai_block_reason(project_with_transcript(), make_settings(tmp_path))


def test_demo_stories_may_use_live_ai_with_any_key(tmp_path):
    settings = make_settings(tmp_path, gemini_api_key="k")
    assert external_ai_block_reason(project_with_transcript(kind="synthetic_dev"), settings) is None
    assert external_ai_block_reason(project_with_transcript(kind="self_demo"), settings) is None


def test_a_real_storyteller_needs_specific_consent_and_a_paid_plan(tmp_path):
    free_key = make_settings(tmp_path, gemini_api_key="k")
    paid_key = make_settings(tmp_path, gemini_api_key="k", gemini_prompts_not_used_for_training=True)
    assert "specifically agreed" in external_ai_block_reason(storyteller(), paid_key)
    assert "not marked as a paid plan" in external_ai_block_reason(storyteller(agreed_external_ai=True), free_key)
    assert external_ai_block_reason(storyteller(agreed_external_ai=True), paid_key) is None
    assert external_ai_block_reason(storyteller(agreed_external_ai=True, withdrawn=True), paid_key) is not None


def test_live_ai_needs_the_family_name_and_pronouns_first(tmp_path):
    store, project = stored_project(tmp_path, named=False)
    live = FakeLive(three_pages())
    with pytest.raises(DraftError, match="fill in"):
        draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"), live=live)
    assert live.calls == 0


def test_a_blocked_real_story_gets_its_own_words_and_says_why(tmp_path):
    store, project = stored_project(tmp_path, kind="storyteller", consent=make_consent())  # no outside-AI agreement
    made = draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"))
    [warning] = made.warnings
    assert "not used" in warning.message and "specifically agreed" in warning.message and "own words" in warning.message


# --- live AI: what happens ------------------------------------------------------------------------------

def test_a_live_draft_becomes_the_pages_and_is_saved_for_offline_replay(tmp_path):
    store, project = stored_project(tmp_path)
    made = draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"), live=FakeLive(three_pages(title="Gram's Day")))
    assert made.drafted_by == "Fake AI" and made.suggested_title == "Gram's Day" and len(made.chapters) == 3
    saved = json.loads((store.project_dir(project.id) / "ai_draft.json").read_text(encoding="utf-8"))
    assert saved["drafted_by"] == "Fake AI, saved draft" and saved["transcript_fingerprint"] == transcript_fingerprint(project)

    replayed = draft_story(store, store.load(project.id), make_settings(tmp_path), replay=True)
    assert replayed.drafted_by == "Fake AI, saved draft" and len(replayed.chapters) == 3


def test_when_the_ai_service_fails_the_book_still_gets_made_and_the_person_is_told(tmp_path):
    store, project = stored_project(tmp_path)
    made = draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"),
                       live=FakeLive(ProviderError("Could not reach Google's AI service.")))
    [warning] = made.warnings
    assert "Could not reach" in warning.message and "own words" in warning.message and made.chapters


def test_a_successful_draft_clears_an_old_warning(tmp_path):
    store, project = stored_project(tmp_path)
    draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"), live=FakeLive(ProviderError("down")))
    made = draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"), live=FakeLive(three_pages()))
    assert made.warnings == []


def test_an_answer_that_does_not_fit_is_retried_once(tmp_path):
    store, project = stored_project(tmp_path)
    live = FakeLive(story(page("seg-9999")), three_pages())
    made = draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"), live=live)
    assert live.calls == 2 and made.drafted_by == "Fake AI"


def test_two_bad_answers_in_a_row_give_up_and_change_nothing(tmp_path):
    store, project = stored_project(tmp_path)
    bad = story(page("seg-9999"))
    live = FakeLive(bad, bad)
    with pytest.raises(DraftError):
        draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"), live=live)
    assert live.calls == 2 and project.chapters == []
    assert not (store.project_dir(project.id) / "ai_draft.json").exists()


def test_replay_never_calls_the_live_service(tmp_path):
    store, project = stored_project(tmp_path)
    live = FakeLive()
    draft_story(store, project, make_settings(tmp_path, gemini_api_key="k"), live=live, replay=True)
    assert live.calls == 0


def test_pictures_stay_with_their_page_number_when_the_story_is_remade(tmp_path):
    store, project = stored_project(tmp_path)
    settings = make_settings(tmp_path, gemini_api_key="k")
    draft_story(store, project, settings, live=FakeLive(three_pages()))
    photos = store.project_dir(project.id) / "photos"
    photos.mkdir()
    for page_id, name in (("p1", "a" * 32), ("p3", "b" * 32)):
        (photos / f"{name}.jpg").write_bytes(b"x")
        next(c for c in project.chapters if c.id == page_id).photo_file = f"photos/{name}.jpg"
    remade = draft_story(store, project, settings, live=FakeLive(story(page("seg-0001"), page("seg-0009"))))
    assert remade.chapters[0].photo_file == f"photos/{'a' * 32}.jpg"
    assert not (photos / f"{'b' * 32}.jpg").exists()  # page 3 is gone, so its picture was deleted


# --- reviewing sentences --------------------------------------------------------------------------------

def reviewed_project():
    project = project_with_transcript()
    apply_drafts(project, three_pages(), "p")
    return project


def test_approving_removing_and_restoring_a_sentence():
    project = reviewed_project()
    assert update_sentence(project, "p1-s1", status="approved").status == "approved"
    assert update_sentence(project, "p1-s1", status="removed").status == "removed"
    assert update_sentence(project, "p1-s1", status="flagged").status == "flagged"


def test_rewriting_a_sentence_marks_it_human_written_and_reviewed():
    sentence = update_sentence(reviewed_project(), "p1-s1", text="  My own wording.  ")
    assert (sentence.text, sentence.edit_type, sentence.status) == ("My own wording.", "volunteer_caption", "approved")


def test_saving_unchanged_text_keeps_the_edit_type():
    sentence = update_sentence(reviewed_project(), "p1-s1", text="A drafted sentence.")
    assert (sentence.edit_type, sentence.status) == ("ai_draft", "approved")


def test_blank_text_and_unknown_sentences_are_rejected():
    project = reviewed_project()
    with pytest.raises(DraftError):
        update_sentence(project, "p1-s1", text="   ")
    with pytest.raises(SentenceNotFound):
        update_sentence(project, "p9-s9", status="approved")


# --- asking for changes and confirming the story ----------------------------------------------------

from app.providers.base import Revision  # noqa: E402
from app.services.drafting import (  # noqa: E402
    HelperUnavailable,
    ai_helper_status,
    confirm_story,
    pages_from_revision,
    revise_story,
)


class FakeReviser:
    """Stands in for Gemini's revise_story: returns scripted answers or raises ProviderError."""

    name = "Fake AI"

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def revise_story(self, project, request):
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def as_revision(project, title=None, reply="Done.", insert_at=None, new_text="A new page.", sources=()):
    """The current book as a Revision, optionally with one new page inserted."""
    pages = [{"from_page": c.id, "photo_idea": c.photo_idea,
              "sentences": [{"text": s.text, "source_segment_ids": s.source_segment_ids} for s in c.sentences
                            if s.status != "removed"]}
             for c in project.chapters]
    if insert_at is not None:
        pages.insert(insert_at, {"from_page": "new", "photo_idea": "a cake",
                                 "sentences": [{"text": new_text, "source_segment_ids": list(sources)}]})
    return Revision(book_title=title, reply=reply, pages=pages)


def confirmed_book(tmp_path):
    store, project = stored_project(tmp_path)
    project.chapters = pages_from_draft(project, story(
        page("seg-0001", text="Gram biked to school."), page("seg-0009", text="She had two cows."),
        page("seg-0017", text="She loved Sundays.")))
    project.chapters[1].photo_file = "photos/cows.jpg"
    project.suggested_title = "Gram's Day"
    confirm_story(project)
    store.save(project)
    return store, project


def test_confirming_approves_everything_still_waiting_to_be_read(tmp_path):
    _store, project = stored_project(tmp_path)
    project.chapters = pages_from_draft(project, three_pages())
    project.chapters[0].sentences[0].status = "removed"
    assert confirm_story(project) == 2
    assert [s.status for c in project.chapters for s in c.sentences] == ["removed", "approved", "approved"]
    with pytest.raises(DraftError):
        confirm_story(StoryProject(id="abcd1234", recording_kind="synthetic_dev"))


def test_an_unchanged_book_comes_back_unchanged(tmp_path):
    _store, project = confirmed_book(tmp_path)
    pages, changed = pages_from_revision(project, as_revision(project))
    assert changed == []
    assert [c.model_dump() for c in pages] == [c.model_dump() for c in project.chapters]


def test_a_new_page_needs_reading_and_pictures_stay_with_their_page(tmp_path):
    _store, project = confirmed_book(tmp_path)
    pages, changed = pages_from_revision(project, as_revision(project, insert_at=1, sources=["seg-0005"]))
    assert [c.id for c in pages] == ["p1", "p2", "p3", "p4"]
    assert changed == [3]  # page 3 of the book (the cover is page 1)
    assert pages[1].sentences[0].status == "flagged" and pages[1].sentences[0].edit_type == "ai_draft"
    assert pages[2].photo_file == "photos/cows.jpg" and pages[1].photo_file is None  # the cows moved down with their page
    assert all(s.status == "approved" for c in (pages[0], pages[2], pages[3]) for s in c.sentences)
    assert pages[2].sentences[0].id == "p3-s1"


def test_a_sentence_from_the_familys_message_has_no_recording_lines(tmp_path):
    _store, project = confirmed_book(tmp_path)
    pages, _changed = pages_from_revision(project, as_revision(project, insert_at=3, new_text="The end, with love."))
    last = pages[3]
    assert last.segment_ids == [] and last.sentences[0].source_segment_ids == []
    assert (last.clip_start, last.clip_end) == (0.0, 0.0)


def test_a_revision_must_not_point_at_lines_that_do_not_exist(tmp_path):
    _store, project = confirmed_book(tmp_path)
    with pytest.raises(DraftError):
        pages_from_revision(project, as_revision(project, insert_at=0, sources=["seg-9999"]))


def test_one_picture_is_never_used_on_two_pages(tmp_path):
    _store, project = confirmed_book(tmp_path)
    revision = as_revision(project)
    revision.pages.insert(2, revision.pages[1].model_copy(update={"sentences": [
        DraftSentence(text="The cows were brown.", source_segment_ids=["seg-0010"])]}))
    pages, _changed = pages_from_revision(project, revision)
    assert [c.photo_file for c in pages] == [None, "photos/cows.jpg", None, None]


def test_revise_story_changes_the_book_and_keeps_confirmed_sentences(tmp_path):
    store, project = confirmed_book(tmp_path)
    project.book_title = "A title a person typed"
    revision = as_revision(project, reply=" Added a page. ", insert_at=3, sources=["seg-0020"])
    revision.book_title = "A title a person typed"
    fake = FakeReviser(revision)
    project, reply, changed = revise_story(store, project, make_settings(tmp_path), "  Add the cake.  ", live=fake)
    assert fake.requests == ["Add the cake."]
    assert reply == "Added a page." and changed == [5]
    assert project.book_title == "A title a person typed"  # an unchanged title stays
    assert store.load(project.id).chapters[3].sentences[0].text == "A new page."


def test_asking_for_a_new_title_replaces_a_typed_title(tmp_path):
    store, project = confirmed_book(tmp_path)
    project.book_title = "Old title"
    fake = FakeReviser(as_revision(project, title="Gram's Farm"))
    project, _reply, _changed = revise_story(store, project, make_settings(tmp_path), "Call it Gram's Farm", live=fake)
    assert (project.book_title, project.suggested_title) == (None, "Gram's Farm")


def test_an_answer_that_does_not_fit_is_retried_once_then_nothing_changes(tmp_path):
    store, project = confirmed_book(tmp_path)
    before = [c.model_dump() for c in project.chapters]
    bad = as_revision(project, insert_at=0, sources=["seg-9999"])
    fake = FakeReviser(bad, bad)
    with pytest.raises(HelperUnavailable):
        revise_story(store, project, make_settings(tmp_path), "Change it", live=fake)
    assert len(fake.requests) == 2
    assert [c.model_dump() for c in store.load(project.id).chapters] == before

    good = FakeReviser(bad, as_revision(project))
    revise_story(store, project, make_settings(tmp_path), "Change it", live=good)
    assert len(good.requests) == 2


def test_a_service_error_changes_nothing(tmp_path):
    store, project = confirmed_book(tmp_path)
    with pytest.raises(HelperUnavailable) as error:
        revise_story(store, project, make_settings(tmp_path), "Change it", live=FakeReviser(ProviderError("busy")))
    assert "Nothing was changed" in str(error.value)


@pytest.mark.parametrize("request_text", ["", "   ", "x" * 1001])
def test_change_requests_must_be_typed_and_short(tmp_path, request_text):
    store, project = confirmed_book(tmp_path)
    with pytest.raises(DraftError):
        revise_story(store, project, make_settings(tmp_path), request_text, live=FakeReviser())


def test_a_real_storytellers_words_are_not_sent_without_their_consent(tmp_path):
    consent = make_consent(agreed_external_ai=False)
    store, project = stored_project(tmp_path, kind="storyteller", consent=consent)
    project.chapters = pages_from_draft(project, three_pages())
    settings = make_settings(tmp_path, gemini_api_key="key", gemini_prompts_not_used_for_training=True)
    status = ai_helper_status(project, settings)
    assert status["available"] is False and "agreed" in status["reason"]
    with pytest.raises(HelperUnavailable):
        revise_story(store, project, settings, "Change it")
