"""Making the storybook pages, changing them on request, and confirming them.

"Make the storybook" turns the whole transcript into picture-book pages:
- Live AI (Google Gemini) when a key is set AND sending this story's text is allowed. Its sentences enter
  the book as "ai_draft" sentences that NEED READING (status "flagged"). Each live draft is saved
  (ai_draft.json) for offline replay.
- Otherwise, or if the AI service fails, a saved draft made from this same transcript.
- Otherwise, the storyteller's own words, a few lines per page.
Pages are stored as chapters (one chapter = one page of the book).

Then a person reads the story with the storyteller or family:
- "Ask for changes": the reviewer types a request and the AI rewrites the book (revise_story). Only new or
  changed sentences need reading again.
- Small fixes can also be made by hand (update_sentence).
- "The story is right" (confirm_story) approves what they read. Nothing can be exported before that.
"""
import hashlib
import json
from pathlib import Path

from ..config import REPO_ROOT, Settings
from ..providers.base import ProviderError, Revision, StoryDraft, StoryProvider
from ..providers.fixture import FixtureProvider
from ..providers.gemini import GeminiProvider
from ..schemas import BookSentence, Chapter, ProjectWarning, SentenceStatus, StoryProject
from .book_pdf import book_title_for
from .photos import forget_photo
from .storage import ProjectStore
from .structure import build_chapters

SYNTHETIC_FIXTURE = REPO_ROOT / "fixtures" / "drafts" / "synthetic_story.ai_draft.json"
AI_WARNING = "ai_unavailable"
OWN_WORDS_LINES_PER_PAGE = 3
MAX_REQUEST_CHARS = 1000
_AUTO = object()


class DraftError(Exception):
    """A draft does not fit the project (unknown lines, no sentences, ...)."""


class HelperUnavailable(Exception):
    """The AI can't carry out a requested change right now (not allowed, no key, or the service failed)."""


class SentenceNotFound(Exception):
    pass


def transcript_fingerprint(project: StoryProject) -> str:
    """Identifies the exact transcript a draft was made from."""
    text = "\n".join(f"{s.id} {s.text}" for s in project.transcript)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def external_ai_block_reason(project: StoryProject, settings: Settings) -> str | None:
    """Why this story's text must NOT be sent to Google's AI service, or None if it may be."""
    if not settings.gemini_api_key:
        return "No Gemini API key is set."
    if project.recording_kind == "storyteller":
        consent = project.consent
        if not (consent and consent.agreed_external_ai and not consent.withdrawn):
            return "The storyteller has not specifically agreed to their words being sent to Google's AI service."
        if not settings.gemini_prompts_not_used_for_training:
            return (
                "This Gemini key is not marked as a paid plan. Google may use text sent through free keys to improve "
                "its products, and people there may read it, so a real storyteller's words are not sent. (Set "
                "GEMINI_PROMPTS_NOT_USED_FOR_TRAINING=true only if the key belongs to a billing-enabled Google project.)"
            )
    return None


def live_provider(project: StoryProject, settings: Settings) -> StoryProvider | None:
    if external_ai_block_reason(project, settings) is not None:
        return None
    return GeminiProvider(settings.gemini_api_key, settings.gemini_model)


def saved_provider(store: ProjectStore, project: StoryProject, synthetic_fixture: Path = SYNTHETIC_FIXTURE) -> StoryProvider | None:
    """A saved draft made from THIS transcript (a draft for another recording must never be used)."""
    fingerprint = transcript_fingerprint(project)
    saved = store.project_dir(project.id) / "ai_draft.json"
    if saved.is_file() and FixtureProvider(saved).fingerprint in (None, fingerprint):  # None: saved before fingerprints
        return FixtureProvider(saved)
    if project.recording_kind == "synthetic_dev" and synthetic_fixture.is_file():
        sample = FixtureProvider(synthetic_fixture)
        if sample.fingerprint == fingerprint:
            return sample
    return None


def pages_from_draft(project: StoryProject, story: StoryDraft) -> list[Chapter]:
    """Check a draft and turn it into book pages. Every sentence must point at real transcript lines."""
    segments = {s.id: s for s in project.transcript}
    order = {s.id: i for i, s in enumerate(project.transcript)}
    pages: list[Chapter] = []
    for draft in story.pages:
        number = len(pages) + 1
        sentences = []
        for item in draft.sentences:
            text = item.text.strip()
            if not text:
                continue
            if not item.source_segment_ids:
                raise DraftError(f"A sentence on page {number} does not say where in the recording it came from.")
            unknown = [i for i in item.source_segment_ids if i not in segments]
            if unknown:
                raise DraftError(f"A sentence on page {number} points at lines that are not in this recording: {unknown}.")
            sentences.append(BookSentence(
                id=f"p{number}-s{len(sentences) + 1}", text=text, source_segment_ids=item.source_segment_ids,
                edit_type="ai_draft", grounding_score=None, status="flagged",
            ))
        if not sentences:
            continue
        cited = sorted({i for s in sentences for i in s.source_segment_ids}, key=order.get)
        pages.append(Chapter(
            id=f"p{number}", title=f"Page {number}", sentences=sentences, segment_ids=cited,
            clip_start=min(segments[i].start for i in cited), clip_end=max(segments[i].end for i in cited),
            photo_idea=(draft.photo_idea or "").strip() or None,
        ))
    if not pages:
        raise DraftError("The draft has no sentences.")
    return pages


def own_words_pages(project: StoryProject, lines_per_page: int = OWN_WORDS_LINES_PER_PAGE) -> list[Chapter]:
    """The storyteller's own transcribed words, a few lines per page (used when no AI may be used)."""
    starts = list(range(0, len(project.transcript), lines_per_page))
    pages = build_chapters(project.transcript, starts)
    for number, page in enumerate(pages, start=1):
        page.id, page.title = f"p{number}", f"Page {number}"
        for position, sentence in enumerate(page.sentences, start=1):
            sentence.id = f"p{number}-s{position}"
    return pages


def _use_pages(store: ProjectStore, project: StoryProject, pages: list[Chapter]) -> None:
    """Replace the pages; pictures stay with their page number, and pictures of pages that are gone are deleted."""
    old = {c.id: c for c in project.chapters}
    for page in pages:
        if page.id in old:
            page.photo_file, page.photo_caption = old[page.id].photo_file, old[page.id].photo_caption
    kept = {p.id for p in pages}
    project.chapters = pages
    for gone in (c for c in old.values() if c.id not in kept):
        forget_photo(store, project, gone.photo_file)


def _apply_draft(store: ProjectStore, project: StoryProject, story: StoryDraft, source: str) -> None:
    _use_pages(store, project, pages_from_draft(project, story))
    if story.book_title and story.book_title.strip():
        project.suggested_title = story.book_title.strip()  # a title a person typed (book_title) still wins
    project.drafted_by = source


def apply_drafts(project: StoryProject, story: StoryDraft, source: str) -> StoryProject:
    """Apply a draft to a project in memory (no files touched). Nothing changes if the draft is invalid."""
    pages = pages_from_draft(project, story)
    project.chapters = pages
    if story.book_title and story.book_title.strip():
        project.suggested_title = story.book_title.strip()
    project.drafted_by = source
    return project


def _ask_live(provider: StoryProvider, project: StoryProject) -> StoryDraft:
    """Ask the live provider; one retry if its answer doesn't fit. Service errors are not retried here."""
    for attempt in (1, 2):
        story = provider.draft_story(project)
        try:
            pages_from_draft(project, story)
            return story
        except DraftError:
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


def _save_copy(store: ProjectStore, project: StoryProject, story: StoryDraft, source: str) -> None:
    payload = {
        "drafted_by": f"{source}, saved draft",
        "note": "Saved copy of an AI draft for offline replay. Delete this file to forget it.",
        **story.model_dump(mode="json"),
        "transcript_fingerprint": transcript_fingerprint(project),
    }
    (store.project_dir(project.id) / "ai_draft.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def draft_story(
    store: ProjectStore, project: StoryProject, settings: Settings, live=_AUTO, replay: bool = False
) -> StoryProject:
    """Make the storybook pages from the transcript (see the module docstring for which way is used)."""
    if not project.transcript:
        raise DraftError("Turn the recording into text first.")
    block_reason = None if replay else external_ai_block_reason(project, settings)
    if replay:
        live = None  # replay means saved drafts only: nothing is sent anywhere
    elif live is _AUTO:
        live = live_provider(project, settings)
    if live is not None and (not project.family_name or not project.pronouns):
        raise DraftError("Before making the storybook, fill in what the family calls the storyteller and their pronouns.")
    project.warnings = [w for w in project.warnings if w.code != AI_WARNING]

    unavailable = None
    if live is not None:
        try:
            story = _ask_live(live, project)
        except ProviderError as error:
            unavailable = f"Could not use Google's AI service ({error})"
        else:
            _apply_draft(store, project, story, live.name)
            _save_copy(store, project, story, live.name)
            store.save(project)
            return project
    elif block_reason and settings.gemini_api_key:
        unavailable = f"Google's AI service was not used. {block_reason}"

    saved = saved_provider(store, project)
    if saved is not None:
        _apply_draft(store, project, saved.draft_story(project), saved.name)
        if unavailable:
            project.warnings.append(ProjectWarning(code=AI_WARNING, message=f"{unavailable}. The saved draft was used instead."))
    else:
        _use_pages(store, project, own_words_pages(project))
        project.drafted_by = None
        reason = unavailable or "No AI story writer is available for this story."
        project.warnings.append(ProjectWarning(
            code=AI_WARNING, message=f"{reason}. The pages use the storyteller's own words instead."))
    store.save(project)
    return project


def _same_words(text: str) -> str:
    return " ".join(text.split())


def pages_from_revision(project: StoryProject, revision: Revision) -> tuple[list[Chapter], list[int]]:
    """Check a revised book and turn it into pages. Returns the pages and the page numbers that changed
    (as the reviewer sees them: the cover is page 1).

    - A sentence that is word for word the same as before keeps its status (a confirmed sentence stays
      confirmed). A new or changed sentence is "ai_draft" and needs reading again (status "flagged").
    - Pictures follow their page (from_page), so adding or removing a page does not move them. A picture
      whose page was dropped is kept on disk but no longer used.
    - A sentence may have no transcript lines only when it is based on the reviewer's own request.
    """
    segments = {s.id: s for s in project.transcript}
    order = {s.id: i for i, s in enumerate(project.transcript)}
    old_pages = {c.id: c for c in project.chapters}
    before = {_same_words(s.text): s for c in project.chapters for s in c.sentences if s.status != "removed"}
    used_photos: set[str] = set()
    pages: list[Chapter] = []
    changed: list[int] = []
    for draft in revision.pages:
        number = len(pages) + 1
        old = old_pages.get((draft.from_page or "").strip())
        sentences: list[BookSentence] = []
        for item in draft.sentences:
            text = item.text.strip()
            if not text:
                continue
            sentence_id = f"p{number}-s{len(sentences) + 1}"
            same = before.get(_same_words(text))
            if same is not None:
                sentences.append(same.model_copy(update={"id": sentence_id}))
                continue
            unknown = [i for i in item.source_segment_ids if i not in segments]
            if unknown:
                raise DraftError(f"A sentence on page {number + 1} points at lines that are not in this recording: {unknown}.")
            sentences.append(BookSentence(
                id=sentence_id, text=text, source_segment_ids=list(dict.fromkeys(item.source_segment_ids)),
                edit_type="ai_draft", grounding_score=None, status="flagged",
            ))
        if not sentences:
            continue
        cited = sorted({i for s in sentences for i in s.source_segment_ids}, key=order.get)
        photo = old.photo_file if old and old.photo_file not in used_photos else None
        if photo:
            used_photos.add(photo)
        pages.append(Chapter(
            id=f"p{number}", title=f"Page {number}", sentences=sentences, segment_ids=cited,
            clip_start=min((segments[i].start for i in cited), default=0.0),
            clip_end=max((segments[i].end for i in cited), default=0.0),
            photo_idea=(draft.photo_idea or "").strip() or (old.photo_idea if old else None),
            photo_file=photo, photo_caption=old.photo_caption if photo else None,
        ))
        old_words = [_same_words(s.text) for s in old.sentences if s.status != "removed"] if old else None
        if [_same_words(s.text) for s in sentences] != old_words:
            changed.append(number + 1)
    if not pages:
        raise DraftError("The changed story has no sentences left.")
    return pages, changed


def ai_helper_status(project: StoryProject, settings: Settings) -> dict:
    """Whether the "ask for changes" helper can be used for this story, and if not, why."""
    reason = external_ai_block_reason(project, settings)
    return {"available": reason is None, "reason": reason}


def revise_story(
    store: ProjectStore, project: StoryProject, settings: Settings, request: str, live=_AUTO
) -> tuple[StoryProject, str, list[int]]:
    """Carry out a reviewer's request ("her friend's name is Dotty", "make page 3 shorter") with the AI.

    Returns the project, the AI's short reply, and the page numbers that changed. Changed sentences need
    reading again before the book can be shared. Nothing is changed if the AI's answer does not fit."""
    request = request.strip()
    if not request:
        raise DraftError("Type what you would like to change.")
    if len(request) > MAX_REQUEST_CHARS:
        raise DraftError(f"Please keep each request under {MAX_REQUEST_CHARS} characters.")
    if not project.chapters:
        raise DraftError("Make the storybook first.")
    if live is _AUTO:
        reason = external_ai_block_reason(project, settings)
        if reason:
            raise HelperUnavailable(f"{reason} You can still fix words by hand under each page.")
        live = live_provider(project, settings)
    if not project.family_name or not project.pronouns:
        raise DraftError("Fill in what the family calls the storyteller and their pronouns first.")

    for attempt in (1, 2):
        try:
            revision = live.revise_story(project, request)
        except ProviderError as error:
            raise HelperUnavailable(f"Could not use Google's AI service ({error}). Nothing was changed.") from error
        try:
            pages, changed = pages_from_revision(project, revision)
            break
        except DraftError:
            if attempt == 2:
                raise HelperUnavailable("The AI's answer did not fit the book, so nothing was changed. "
                                        "Try asking in a different way.")

    title = (revision.book_title or "").strip()
    if title and title != book_title_for(project):
        project.suggested_title, project.book_title = title, None  # the newest request wins over a typed title
    project.chapters = pages
    store.save(project)
    return project, revision.reply.strip(), changed


def confirm_story(project: StoryProject) -> int:
    """A person read the whole story (with the storyteller or family) and says it is right.
    Every sentence still waiting to be read counts as approved. Returns how many there were."""
    if not project.chapters:
        raise DraftError("Make the storybook first.")
    waiting = [s for c in project.chapters for s in c.sentences if s.status == "flagged"]
    for sentence in waiting:
        sentence.status = "approved"
    return len(waiting)


def update_sentence(
    project: StoryProject, sentence_id: str, status: SentenceStatus | None = None, text: str | None = None
) -> BookSentence:
    """A person's change to one sentence by hand: remove it, put it back, or rewrite it."""
    sentence = next((s for chapter in project.chapters for s in chapter.sentences if s.id == sentence_id), None)
    if sentence is None:
        raise SentenceNotFound(sentence_id)

    if text is not None:
        text = text.strip()
        if not text:
            raise DraftError("A sentence cannot be empty. Remove it instead.")
        if text != sentence.text:
            sentence.text = text
            sentence.edit_type = "volunteer_caption"  # a person changed it
            sentence.grounding_score = None
        sentence.status = status or "approved"  # rewriting a sentence counts as reviewing it
    elif status is not None:
        sentence.status = status
    return sentence
