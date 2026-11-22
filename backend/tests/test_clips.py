import shutil
import subprocess

import pytest

from app.config import Settings
from app.schemas import Chapter
from app.services.clips import build_clips, clip_bounds
from app.services.record import add_audio
from app.services.storage import ProjectStore
from test_record import sine_wav_bytes

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg/ffprobe not on PATH"
)


def test_clip_bounds_adds_padding():
    assert clip_bounds(10.0, 20.0, 60.0, 0.25) == (9.75, 20.25)


def test_clip_bounds_stay_inside_the_recording():
    assert clip_bounds(0.1, 59.9, 60.0, 0.25) == (0.0, 60.0)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path, models_dir=tmp_path / "models", ffmpeg=shutil.which("ffmpeg") or "ffmpeg",
        whisper_model="small", base_url="http://localhost:8000", clip_padding_seconds=0.25,
    )


def duration_of(path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout)


@needs_ffmpeg
def test_build_clips_cuts_one_mp3_per_chapter(tmp_path, settings):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="synthetic_dev")
    project = add_audio(store, project, "story.wav", sine_wav_bytes(6.0), settings)
    project.chapters = [
        Chapter(id="ch1", title="One", clip_start=1.0, clip_end=3.0, segment_ids=["s0"]),
        Chapter(id="ch2", title="Two", clip_start=3.0, clip_end=5.0, segment_ids=["s1"]),
        Chapter(id="ch3", title="From the family's message only", clip_start=0, clip_end=0),
    ]

    assert build_clips(store, project, settings) == ["ch1.mp3", "ch2.mp3"]  # ch3 has nothing to hear
    for name in ("ch1.mp3", "ch2.mp3"):
        # 2.0 s chapter + 0.25 s padding each side = 2.5 s (the MP3 encoder adds a few hundredths)
        assert duration_of(store.project_dir(project.id) / "clips" / name) == pytest.approx(2.5, abs=0.15)


def test_build_clips_needs_audio_and_chapters(tmp_path, settings):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="synthetic_dev")
    with pytest.raises(ValueError):
        build_clips(store, project, settings)
