"""Settings for StoryBridge, read from environment variables.

A `.env` file at the repo root is also read (see .env.example); real environment variables win.
"""
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Shown on every generated draft (title page, review screen).
REVIEW_NOTICE = (
    "Draft for review with the storyteller. "
    "Every sentence should be confirmed by the senior or their family before sharing."
)


def _read_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    models_dir: Path
    ffmpeg: str
    whisper_model: str
    base_url: str  # QR codes in the PDF point here; must be reachable from the phone that scans them
    clip_padding_seconds: float  # extra audio kept before/after each chapter clip
    gemini_api_key: str | None = field(default=None, repr=False)  # server-side only; repr=False keeps it out of logs
    gemini_model: str = "gemini-3.5-flash"
    # Set true ONLY if the key belongs to a billing-enabled Google project. Google may use text sent through
    # free keys to improve its products, so a real storyteller's words are not sent unless this is true.
    gemini_prompts_not_used_for_training: bool = False


def load_settings() -> Settings:
    _read_dotenv(REPO_ROOT / ".env")
    return Settings(
        data_dir=Path(os.environ.get("STORYBRIDGE_DATA_DIR", REPO_ROOT / "data")),
        models_dir=Path(os.environ.get("STORYBRIDGE_MODELS_DIR", REPO_ROOT / "models")),
        ffmpeg=os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg") or "ffmpeg",
        whisper_model=os.environ.get("WHISPER_MODEL", "small"),
        base_url=os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/"),
        clip_padding_seconds=float(os.environ.get("CLIP_PADDING_SECONDS", "0.25")),
        gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        gemini_prompts_not_used_for_training=os.environ.get(
            "GEMINI_PROMPTS_NOT_USED_FOR_TRAINING", "false"
        ).strip().lower() in {"1", "true", "yes"},
    )
