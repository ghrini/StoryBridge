"""Offline provider: replays a draft that was written earlier and saved as a JSON file.
Needs no key and no internet, so the demonstration can never be blocked by an API.

A saved draft may carry a "drafted_by" label (for example when it was first made by a live AI provider),
which is then shown in the book, and a "transcript_fingerprint" saying which transcript it was made from.
"""
import json
from pathlib import Path

from ..schemas import StoryProject
from .base import StoryDraft


class FixtureProvider:
    def __init__(self, path: Path):
        self.path = Path(path)

    def _data(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @property
    def name(self) -> str:
        return self._data().get("drafted_by") or f"pre-written draft ({self.path.name})"

    @property
    def fingerprint(self) -> str | None:
        return self._data().get("transcript_fingerprint")

    def draft_story(self, project: StoryProject) -> StoryDraft:
        return StoryDraft.model_validate(json.loads(self.path.read_text(encoding="utf-8")))
