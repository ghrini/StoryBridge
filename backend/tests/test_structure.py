"""Spec for the student-written structure.build_chapters. These fail until you implement it."""
import pytest

from app.schemas import TranscriptSegment
from app.services.structure import build_chapters


def make_transcript(count: int) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(id=f"seg-{i + 1:04d}", text=f"Sentence number {i + 1}.", start=i * 2.0, end=i * 2.0 + 1.5)
        for i in range(count)
    ]


def test_splits_segments_into_chapters_at_the_chosen_starts():
    chapters = build_chapters(make_transcript(5), [0, 3])
    assert [len(c.sentences) for c in chapters] == [3, 2]


def test_sentences_are_verbatim_approved_and_ungraded():
    transcript = make_transcript(3)
    [chapter] = build_chapters(transcript, [0])
    for sentence, segment in zip(chapter.sentences, transcript):
        assert sentence.text == segment.text
        assert sentence.source_segment_ids == [segment.id]
        assert sentence.edit_type == "verbatim"
        assert sentence.status == "approved"
        assert sentence.grounding_score is None


def test_clip_times_run_from_first_segment_start_to_last_segment_end():
    transcript = make_transcript(5)
    first, second = build_chapters(transcript, [0, 3])
    assert (first.clip_start, first.clip_end) == (transcript[0].start, transcript[2].end)
    assert (second.clip_start, second.clip_end) == (transcript[3].start, transcript[4].end)


def test_each_chapter_records_which_transcript_lines_it_covers():
    first, second = build_chapters(make_transcript(5), [0, 3])
    assert first.segment_ids == ["seg-0001", "seg-0002", "seg-0003"]
    assert second.segment_ids == ["seg-0004", "seg-0005"]


def test_default_and_custom_titles():
    chapters = build_chapters(make_transcript(4), [0, 2])
    assert [c.title for c in chapters] == ["Chapter 1", "Chapter 2"]
    chapters = build_chapters(make_transcript(4), [0, 2], titles=["The farm", "The bakery"])
    assert [c.title for c in chapters] == ["The farm", "The bakery"]


def test_ids_are_unique_across_the_book():
    chapters = build_chapters(make_transcript(6), [0, 2, 4])
    chapter_ids = [c.id for c in chapters]
    sentence_ids = [s.id for c in chapters for s in c.sentences]
    assert len(set(chapter_ids)) == len(chapter_ids)
    assert len(set(sentence_ids)) == len(sentence_ids)


def test_segments_before_the_first_start_are_left_out():
    [chapter] = build_chapters(make_transcript(5), [2])
    assert [s.source_segment_ids for s in chapter.sentences] == [["seg-0003"], ["seg-0004"], ["seg-0005"]]


@pytest.mark.parametrize("bad_starts", [[], [0, 0], [3, 1], [0, 5], [-1]])
def test_invalid_chapter_starts_raise_value_error(bad_starts):
    with pytest.raises(ValueError):
        build_chapters(make_transcript(5), bad_starts)


def test_title_count_must_match_chapter_count():
    with pytest.raises(ValueError):
        build_chapters(make_transcript(5), [0, 3], titles=["Only one"])
