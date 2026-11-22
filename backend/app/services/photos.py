"""Photos and scanned drawings for the book. They stay on this computer, in the project's photos/ folder,
and are deleted with the project."""
import io
import re
import uuid
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from ..schemas import StoryProject
from .storage import ProjectStore

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_SIDE_PX = 4000  # enough for an 8 x 8 inch page at 300 dpi, with room to crop
PHOTO_NAME = re.compile(r"^[0-9a-f]{32}\.jpg$")


class PhotoError(Exception):
    """The upload is not a usable photo."""


class PhotoNotFound(Exception):
    pass


def save_photo(store: ProjectStore, project: StoryProject, filename: str, source: BinaryIO) -> str:
    """Check, straighten, and store an uploaded image. Returns its path inside the project."""
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise PhotoError("Please choose a JPG, PNG, or WebP picture.")
    data = source.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise PhotoError("That picture is too large (the limit is 25 MB).")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened)  # phone photos are often stored sideways
            image = image.convert("RGB")
            image.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise PhotoError("That file could not be opened as a picture.") from error

    folder = store.project_dir(project.id) / "photos"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"  # the uploaded file name is never used as a path
    image.save(folder / name, "JPEG", quality=92)
    return f"photos/{name}"


def photo_path(store: ProjectStore, project_id: str, name: str) -> Path:
    if not PHOTO_NAME.fullmatch(name):
        raise PhotoNotFound(name)
    path = store.project_dir(project_id) / "photos" / name
    if not path.is_file():
        raise PhotoNotFound(name)
    return path


def forget_photo(store: ProjectStore, project: StoryProject, relative: str | None) -> None:
    """Delete a stored photo file if nothing in the project still uses it."""
    if not relative:
        return
    still_used = {project.cover_photo, *(c.photo_file for c in project.chapters), *(p.photo_file for p in project.photo_pages)}
    if relative in still_used:
        return
    path = store.project_dir(project.id) / relative
    if path.parent.name == "photos" and PHOTO_NAME.fullmatch(path.name) and path.is_file():
        path.unlink()


def set_cover_photo(store: ProjectStore, project: StoryProject, relative: str | None) -> None:
    old, project.cover_photo = project.cover_photo, relative
    forget_photo(store, project, old)


def set_chapter_photo(store: ProjectStore, project: StoryProject, chapter_id: str, relative: str | None) -> None:
    chapter = next((c for c in project.chapters if c.id == chapter_id), None)
    if chapter is None:
        raise PhotoNotFound(chapter_id)
    old, chapter.photo_file = chapter.photo_file, relative
    if relative is None:
        chapter.photo_caption = None
    forget_photo(store, project, old)


