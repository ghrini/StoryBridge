import io
import math
import shutil
import struct
import wave

import pytest

from app.config import Settings
from app.services.record import AudioError, ConsentError, add_audio
from app.services.storage import ProjectStore
from test_schemas import make_consent

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not on PATH")


def sine_wav_bytes(seconds: float = 2.0, rate: int = 22050) -> io.BytesIO:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        frames = (
            struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / rate)))
            for i in range(int(seconds * rate))
        )
        wav.writeframes(b"".join(frames))
    buffer.seek(0)
    return buffer


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path,
        models_dir=tmp_path / "models",
        ffmpeg=shutil.which("ffmpeg") or "ffmpeg",
        whisper_model="small",
        base_url="http://localhost:8000",
        clip_padding_seconds=0.25,
    )


def test_add_audio_creates_normalized_16k_mono_wav(tmp_path, settings):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="synthetic_dev")
    updated = add_audio(store, project, "my story.wav", sine_wav_bytes(2.0), settings)

    assert updated.audio_file == "audio/story.wav"
    assert updated.duration_seconds == pytest.approx(2.0, abs=0.15)
    with wave.open(str(store.project_dir(project.id) / "audio" / "story.wav"), "rb") as wav:
        assert (wav.getframerate(), wav.getnchannels()) == (16000, 1)
    assert store.load(project.id).audio_file == "audio/story.wav"


def test_add_audio_refuses_without_recording_consent(tmp_path, settings):
    store = ProjectStore(tmp_path)
    project = store.create(consent=make_consent(agreed_recording=False))
    with pytest.raises(ConsentError):
        add_audio(store, project, "story.wav", sine_wav_bytes(), settings)
    assert not (store.project_dir(project.id) / "audio").exists()


def test_add_audio_refuses_after_withdrawal(tmp_path, settings):
    store = ProjectStore(tmp_path)
    project = store.create(consent=make_consent(withdrawn=True))
    with pytest.raises(ConsentError):
        add_audio(store, project, "story.wav", sine_wav_bytes(), settings)


def test_add_audio_rejects_unknown_file_types(tmp_path, settings):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="synthetic_dev")
    with pytest.raises(AudioError):
        add_audio(store, project, "virus.exe", io.BytesIO(b"x"), settings)


def test_add_audio_reports_unreadable_audio(tmp_path, settings):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="synthetic_dev")
    with pytest.raises(AudioError):
        add_audio(store, project, "story.wav", io.BytesIO(b"this is not audio"), settings)
