"""Cut each chapter's audio out of the project's recording. These small MP3 clips are what the
QR codes in the book play."""
from pathlib import Path

from ..config import Settings
from ..schemas import StoryProject
from .record import run_ffmpeg
from .storage import ProjectStore


def clip_bounds(clip_start: float, clip_end: float, duration: float, padding: float) -> tuple[float, float]:
    """Widen a chapter's time range by `padding` seconds each side, staying inside the recording."""
    return max(0.0, clip_start - padding), min(duration, clip_end + padding)


def cut_clip(source: Path, destination: Path, start: float, end: float, ffmpeg: str) -> None:
    run_ffmpeg(
        [
            "-i", str(source), "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}",
            "-vn", "-codec:a", "libmp3lame", "-b:a", "64k", str(destination),
        ],
        ffmpeg,
    )


def build_clips(store: ProjectStore, project: StoryProject, settings: Settings) -> list[str]:
    """Cut one MP3 per chapter into the project's clips/ folder. Returns the file names."""
    if not project.audio_file or project.duration_seconds is None:
        raise ValueError("This project has no audio yet.")
    if not project.chapters:
        raise ValueError("Choose chapters first.")

    source = store.project_dir(project.id) / project.audio_file
    clips_dir = store.project_dir(project.id) / "clips"
    clips_dir.mkdir(exist_ok=True)

    names = []
    for chapter in project.chapters:
        if not chapter.segment_ids:
            continue  # a page written only from the family's message has nothing to hear
        start, end = clip_bounds(
            chapter.clip_start, chapter.clip_end, project.duration_seconds, settings.clip_padding_seconds
        )
        destination = clips_dir / f"{chapter.id}.mp3"
        cut_clip(source, destination, start, end, settings.ffmpeg)
        names.append(destination.name)
    return names
