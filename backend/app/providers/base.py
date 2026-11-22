"""The StoryProvider interface: anything that can turn a project's transcript into picture-book pages.

Rules every provider and the code around it must keep:
- Drafts are only suggestions. They enter the book as "needs review" sentences, never approved.
- Every drafted sentence names the transcript lines it is based on (source_segment_ids). The one
  exception is a revision: a sentence based only on the reviewer's own request has no lines.
- The app must work with no provider and no internet (saved drafts, or the storyteller's own words).
"""
from typing import Protocol

from pydantic import BaseModel, model_validator

from ..schemas import StoryProject


class ProviderError(Exception):
    """A provider could not produce a draft (network down, service error, unusable answer)."""


class DraftSentence(BaseModel):
    text: str
    source_segment_ids: list[str]


class PageDraft(BaseModel):
    photo_idea: str | None = None  # what picture would fit this page
    sentences: list[DraftSentence]


class StoryDraft(BaseModel):
    book_title: str | None = None
    transcript_fingerprint: str | None = None  # which transcript a saved draft was made from
    pages: list[PageDraft]

    @model_validator(mode="before")
    @classmethod
    def _accept_older_chapter_drafts(cls, data):
        # Drafts saved before the book had pages used "chapters"; each chapter becomes one page.
        if isinstance(data, dict) and "pages" not in data and "chapters" in data:
            data = {**data, "pages": [{"photo_idea": c.get("photo_idea"), "sentences": c.get("sentences", [])}
                                      for c in data["chapters"]]}
        return data


class RevisedPage(PageDraft):
    from_page: str | None = None  # id of the current page this page comes from ("p3"), or "new"


class Revision(BaseModel):
    """The whole book again, with a reviewer's requested change carried out."""

    book_title: str | None = None
    reply: str = ""  # a short note to the reviewer about what was changed
    pages: list[RevisedPage]


class StoryProvider(Protocol):
    name: str  # shown in the book and in AI_USE records

    def draft_story(self, project: StoryProject) -> StoryDraft: ...
