"""Local transcription with faster-whisper (CPU, int8). Audio never leaves this computer.
The only network use is a one-time download of the model weights if they are not cached in models/."""
from pathlib import Path

from ..config import Settings
from ..schemas import StoryProject, TranscriptSegment, TranscriptWord
from .storage import ProjectStore

_loaded_models: dict[str, object] = {}


def to_segments(raw_segments) -> list[TranscriptSegment]:
    """Convert faster-whisper segments into our TranscriptSegments with word times."""
    segments: list[TranscriptSegment] = []
    for raw in raw_segments:
        text = raw.text.strip()
        if not text:
            continue
        words = [
            TranscriptWord(word=w.word.strip(), start=w.start, end=max(w.end, w.start))
            for w in (raw.words or [])
            if w.word.strip()
        ]
        segments.append(
            TranscriptSegment(
                id=f"seg-{len(segments) + 1:04d}",
                text=text,
                start=raw.start,
                end=max(raw.end, raw.start),
                words=words,
            )
        )
    return segments


def _load_model(model_name: str, models_dir: Path):
    if model_name not in _loaded_models:
        from faster_whisper import WhisperModel, download_model  # heavy import, so done lazily

        try:
            model_path = download_model(model_name, cache_dir=str(models_dir), local_files_only=True)
        except Exception:
            print(f"Whisper model '{model_name}' is not cached yet; downloading the weights once...")
            model_path = download_model(model_name, cache_dir=str(models_dir))
        _loaded_models[model_name] = WhisperModel(model_path, device="cpu", compute_type="int8")
    return _loaded_models[model_name]


def transcribe_project(store: ProjectStore, project: StoryProject, settings: Settings) -> StoryProject:
    """Transcribe the project's audio. Replaces any earlier transcript and clears chapters,
    because chapters refer to segment ids that a new transcript would change."""
    if not project.audio_file:
        raise ValueError("This project has no audio yet.")
    wav_path = store.project_dir(project.id) / project.audio_file

    model = _load_model(settings.whisper_model, settings.models_dir)
    raw_segments, _info = model.transcribe(str(wav_path), language="en", word_timestamps=True)
    segments = to_segments(raw_segments)  # iterating here is what actually runs the model

    project.transcript = segments
    project.chapters = []
    project.transcription_model = settings.whisper_model
    store.save(project)
    return project
