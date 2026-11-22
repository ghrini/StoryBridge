"""StoryBridge data model. A whole project is stored as one project.json built from these classes."""
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# verbatim = the storyteller's words as transcribed; light_edit = filler removed / minimal grammar fix;
# ai_draft = storybook sentence drafted by an AI provider (always needs human review);
# volunteer_caption = text a person wrote or changed.
EditType = Literal["verbatim", "light_edit", "ai_draft", "volunteer_caption"]
SentenceStatus = Literal["approved", "flagged", "removed"]
AssignmentStatus = Literal["open", "claimed", "uploaded", "approved"]
# storyteller = a real person (consent record required); self_demo = the student's own demo
# recording; synthetic_dev = computer-voice test clip. The book labels non-storyteller kinds as demos.
RecordingKind = Literal["storyteller", "self_demo", "synthetic_dev"]


class ConsentRecord(BaseModel):
    """What the storyteller agreed to. Each permission is a separate yes/no."""

    agreed_on: date
    agreed_recording: bool
    agreed_local_transcription: bool
    agreed_book: bool  # a book may be made from their words
    agreed_audio_qr: bool  # QR codes may play their voice
    agreed_video: bool  # voice/name/photo/quote may appear in the demo video
    agreed_external_ai: bool = False  # audio/transcript may be sent to an outside AI service (default: no)
    facility_permission: Literal["not_applicable", "granted"] = "not_applicable"
    withdrawn: bool = False  # if true, the recording must be deleted
    withdrawn_on: date | None = None
    notes: str = ""


class TranscriptWord(BaseModel):
    word: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)


class TranscriptSegment(BaseModel):
    id: str
    text: str
    start: float = Field(ge=0)  # seconds from the start of the recording
    end: float = Field(ge=0)
    words: list[TranscriptWord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.end < self.start:
            raise ValueError("segment end must not be before its start")
        return self


class BookSentence(BaseModel):
    id: str
    text: str  # as shown in the book
    source_segment_ids: list[str]
    edit_type: EditType = "verbatim"
    grounding_score: float | None = Field(default=None, ge=0, le=1)  # None until the grounding check runs
    status: SentenceStatus = "approved"


class Chapter(BaseModel):
    id: str
    title: str
    sentences: list[BookSentence] = Field(default_factory=list)
    clip_start: float = Field(ge=0)  # where the chapter's audio clip starts, in seconds
    clip_end: float = Field(ge=0)
    segment_ids: list[str] = Field(default_factory=list)  # the transcript lines this chapter covers
    photo_file: str | None = None  # a photo or scanned drawing for this chapter's page (path inside the project)
    photo_caption: str | None = None
    photo_idea: str | None = None  # suggestion for what picture would fit, e.g. "a yellow school bus"
    assignment_id: str | None = None  # the illustration request for this chapter

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.clip_end < self.clip_start:
            raise ValueError("chapter clip end must not be before its start")
        return self

    @model_validator(mode="after")
    def _derive_segment_ids(self):
        # Chapters saved before segment_ids existed: recover them from the sentences' sources.
        if not self.segment_ids:
            self.segment_ids = list(dict.fromkeys(i for s in self.sentences for i in s.source_segment_ids))
        return self


class Assignment(BaseModel):
    """An illustration request a SmileCard volunteer can claim."""

    id: str
    chapter_id: str
    prompt: str  # short and non-private, e.g. "a 1950s school bus on a farm road"
    status: AssignmentStatus = "open"
    volunteer_name: str | None = None
    image_file: str | None = None  # path inside the project folder


class PhotoPage(BaseModel):
    """A full-page photo placed between chapters."""

    id: str
    after_chapter_id: str | None = None  # None = right after the opening pages
    photo_file: str
    caption: str | None = None


Pronouns = Literal["she/her", "he/him", "they/them"]


class ProjectWarning(BaseModel):
    code: str  # e.g. "private_detail", "unsupported_sentence"
    message: str
    sentence_id: str | None = None


class StoryProject(BaseModel):
    id: str
    storyteller_name: str | None = None  # optional; may be a first name only
    family_name: str | None = None  # what the family calls them in the book, e.g. "Gram"
    pronouns: Pronouns | None = None  # chosen by a person; never guessed
    book_title: str | None = None  # chosen by a person; wins over the suggestion
    suggested_title: str | None = None  # suggested by the story drafter
    cover_photo: str | None = None
    photo_pages: list[PhotoPage] = Field(default_factory=list)
    recording_kind: RecordingKind = "storyteller"
    consent: ConsentRecord | None = None
    audio_file: str | None = None  # path inside the project folder
    duration_seconds: float | None = None
    transcription_model: str | None = None
    drafted_by: str | None = None  # which provider drafted the storybook text, if any (shown in the book)
    transcript: list[TranscriptSegment] = Field(default_factory=list)
    chapters: list[Chapter] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)
    warnings: list[ProjectWarning] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _storyteller_needs_consent(self):
        if self.recording_kind == "storyteller" and self.consent is None:
            raise ValueError("a storyteller project needs a consent record")
        return self

    def recording_allowed(self) -> bool:
        """True only if audio may be stored and transcribed for this project."""
        if self.recording_kind != "storyteller":
            return True
        consent = self.consent
        return bool(
            consent
            and not consent.withdrawn
            and consent.agreed_recording
            and consent.agreed_local_transcription
        )
