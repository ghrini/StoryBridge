from types import SimpleNamespace

from app.services.transcribe import to_segments


def raw_segment(text, start, end, words=()):
    return SimpleNamespace(
        text=text,
        start=start,
        end=end,
        words=[SimpleNamespace(word=w, start=s, end=e) for w, s, e in words],
    )


def test_converts_text_times_and_words():
    raw = [raw_segment(" Hello there. ", 0.0, 1.5, [(" Hello", 0.0, 0.6), (" there.", 0.7, 1.5)])]
    [segment] = to_segments(raw)
    assert segment.id == "seg-0001"
    assert segment.text == "Hello there."
    assert (segment.start, segment.end) == (0.0, 1.5)
    assert [w.word for w in segment.words] == ["Hello", "there."]


def test_skips_empty_segments_and_keeps_ids_contiguous():
    raw = [raw_segment("One.", 0, 1), raw_segment("   ", 1, 2), raw_segment("Two.", 2, 3)]
    assert [s.id for s in to_segments(raw)] == ["seg-0001", "seg-0002"]


def test_segment_without_word_times_is_fine():
    [segment] = to_segments([SimpleNamespace(text="Hi.", start=0, end=1, words=None)])
    assert segment.words == []


def test_end_before_start_is_clamped_instead_of_crashing():
    [segment] = to_segments([raw_segment("Hi.", 5.0, 4.9)])
    assert segment.end == segment.start == 5.0
