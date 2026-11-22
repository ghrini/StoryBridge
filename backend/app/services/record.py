"""Audio intake: accept an upload only when consent allows it, then convert it with ffmpeg to a
16 kHz mono WAV with normalized loudness (a very quiet test recording transcribed badly)."""
import shutil
import subprocess
import wave
from pathlib import Path
from typing import BinaryIO

from ..config import Settings
from ..schemas import StoryProject
from .storage import ProjectStore

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".mp4", ".webm", ".ogg", ".opus", ".flac"}
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"


class AudioError(Exception):
    """The upload could not be stored or converted."""


class ConsentError(Exception):
    """Recording is not allowed for this project (no consent, or consent withdrawn)."""


def run_ffmpeg(arguments: list[str], ffmpeg: str) -> None:
    """Run ffmpeg with the given arguments; raise AudioError with a readable message on failure."""
    command = [ffmpeg, "-nostdin", "-y", "-v", "error", *arguments]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    except FileNotFoundError as error:
        raise AudioError("ffmpeg was not found. Install it (winget install --id Gyan.FFmpeg --exact) "
                         "and open a new terminal, or set FFMPEG_PATH.") from error
    if result.returncode != 0:
        raise AudioError(f"ffmpeg could not process this audio: {result.stderr.strip()[-300:]}")


def normalize_audio(source: Path, destination: Path, ffmpeg: str) -> None:
    run_ffmpeg(
        ["-i", str(source), "-vn", "-af", LOUDNORM, "-ar", "16000", "-ac", "1", str(destination)],
        ffmpeg,
    )


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def add_audio(
    store: ProjectStore, project: StoryProject, filename: str, source: BinaryIO, settings: Settings
) -> StoryProject:
    """Save an uploaded recording into the project and prepare it for transcription."""
    if not project.recording_allowed():
        raise ConsentError("This project has no consent to record, or consent was withdrawn.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise AudioError(f"Unsupported audio type '{extension}'.")

    audio_dir = store.project_dir(project.id) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # The uploaded file name is never used as a path; we choose the names.
    original = audio_dir / f"original{extension}"
    with original.open("wb") as out:
        shutil.copyfileobj(source, out)

    story = audio_dir / "story.wav"
    normalize_audio(original, story, settings.ffmpeg)

    project.audio_file = "audio/story.wav"
    project.duration_seconds = round(wav_duration_seconds(story), 2)
    store.save(project)
    return project
