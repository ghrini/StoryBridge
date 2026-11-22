"""Turn a transcript plus manually chosen chapter starts into chapters made of transcript sentences.

Written by Claude at the student's request (the student chose not to write this module), so it is
logged in AI_USE.md as AI-generated. Tests: backend/tests/test_structure.py.
"""
from ..schemas import BookSentence, Chapter, TranscriptSegment


def build_chapters(
    transcript: list[TranscriptSegment],
    chapter_starts: list[int],
    titles: list[str] | None = None,
) -> list[Chapter]:
    """Build chapters from segments the volunteer chose as chapter starts.

    chapter_starts: positions in `transcript` where each chapter begins, e.g. [0, 8, 16].
        Chapter i covers transcript[chapter_starts[i] : chapter_starts[i + 1]]; the last chapter
        runs to the end of the transcript. Segments before the first start are left out.
    titles: one title per chapter. If None, use "Chapter 1", "Chapter 2", ...

    Each segment becomes one BookSentence: its text exactly as transcribed, verbatim, approved,
    and not yet graded (grounding_score=None; the grounding check arrives in Phase 2). Whisper
    segments can end mid-sentence, so a sentence may be split across two book sentences until
    Phase 2's split_sentences replaces this one-segment-one-sentence rule.
    """
    if not chapter_starts:
        raise ValueError("Choose at least one chapter start.")
    if any(not 0 <= start < len(transcript) for start in chapter_starts):
        raise ValueError("A chapter start is outside the transcript.")
    if any(later <= earlier for earlier, later in zip(chapter_starts, chapter_starts[1:])):
        raise ValueError("Chapter starts must be in increasing order, with no repeats.")
    if titles is not None and len(titles) != len(chapter_starts):
        raise ValueError("Give one title per chapter.")

    ends = chapter_starts[1:] + [len(transcript)]
    chapters = []
    for number, (begin, end) in enumerate(zip(chapter_starts, ends), start=1):
        segments = transcript[begin:end]
        sentences = [
            BookSentence(
                id=f"ch{number}-s{position}",
                text=segment.text,
                source_segment_ids=[segment.id],
                edit_type="verbatim",
                grounding_score=None,
                status="approved",
            )
            for position, segment in enumerate(segments, start=1)
        ]
        chapters.append(
            Chapter(
                id=f"ch{number}",
                title=titles[number - 1] if titles else f"Chapter {number}",
                sentences=sentences,
                segment_ids=[segment.id for segment in segments],
                clip_start=segments[0].start,
                clip_end=segments[-1].end,
            )
        )
    return chapters
