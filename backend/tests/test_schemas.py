from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import BookSentence, ConsentRecord, StoryProject, TranscriptSegment


def make_consent(**overrides) -> ConsentRecord:
    fields = dict(
        agreed_on=date(2026, 10, 21),
        agreed_recording=True,
        agreed_local_transcription=True,
        agreed_book=True,
        agreed_audio_qr=True,
        agreed_video=False,
    )
    fields.update(overrides)
    return ConsentRecord(**fields)


def test_storyteller_project_needs_a_consent_record():
    with pytest.raises(ValidationError):
        StoryProject(id="abcd1234", recording_kind="storyteller")


def test_demo_kinds_do_not_need_consent():
    assert StoryProject(id="abcd1234", recording_kind="synthetic_dev").recording_allowed()
    assert StoryProject(id="abcd1234", recording_kind="self_demo").recording_allowed()


def test_recording_allowed_with_full_consent():
    project = StoryProject(id="abcd1234", consent=make_consent())
    assert project.recording_allowed()


@pytest.mark.parametrize(
    "overrides",
    [
        {"agreed_recording": False},
        {"agreed_local_transcription": False},
        {"withdrawn": True},
    ],
)
def test_recording_not_allowed_when_consent_is_missing_or_withdrawn(overrides):
    project = StoryProject(id="abcd1234", consent=make_consent(**overrides))
    assert not project.recording_allowed()


def test_external_ai_defaults_to_no():
    assert make_consent().agreed_external_ai is False


def test_segment_end_cannot_precede_start():
    with pytest.raises(ValidationError):
        TranscriptSegment(id="seg-0001", text="hi", start=5.0, end=4.0)


def test_grounding_score_must_be_between_0_and_1_or_none():
    assert BookSentence(id="s1", text="hi", source_segment_ids=[]).grounding_score is None
    with pytest.raises(ValidationError):
        BookSentence(id="s1", text="hi", source_segment_ids=[], grounding_score=1.5)


def test_new_sentence_defaults_to_verbatim_and_approved():
    sentence = BookSentence(id="s1", text="hi", source_segment_ids=["seg-0001"])
    assert (sentence.edit_type, sentence.status) == ("verbatim", "approved")
