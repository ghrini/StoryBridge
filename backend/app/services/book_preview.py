"""Page pictures for the in-app page flipper.

They show the family edition exactly as it will print. If any sentence still needs review, every page
is stamped "PREVIEW", so a screenshot of the flipper can't be mistaken for the finished book. The
pictures stay in the project's preview/ folder and are only served to this computer.
"""
import re
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont

from ..config import REPO_ROOT, Settings
from ..schemas import StoryProject
from .book_pdf import build_pdf

PREVIEW_DPI = 120  # about 960 x 960 pixels per page: sharp on screen, quick to make
PAGE_NAME = re.compile(r"^page-\d{2,3}\.jpg$")
STAMP_TEXT = "PREVIEW - some sentences still need review"
STAMP_COLOR = (106, 63, 176)  # the app's purple


def needs_review(project: StoryProject) -> bool:
    return any(s.status == "flagged" for c in project.chapters for s in c.sentences)


def _stamp(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    band = max(24, image.height // 28)
    try:
        font = ImageFont.truetype(str(REPO_ROOT / "assets" / "fonts" / "Lora-Italic-VF.ttf"), int(band * 0.6))
    except OSError:
        font = ImageFont.load_default()
    draw.rectangle([0, 0, image.width, band], fill=STAMP_COLOR)
    draw.text((band // 2, band // 5), STAMP_TEXT, fill="white", font=font)


def build_preview(project: StoryProject, project_dir: Path, settings: Settings) -> dict:
    """Render every page of the family edition to preview/page-NN.jpg. Returns the names and whether it is reviewed."""
    folder = Path(project_dir) / "preview"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("page-*.jpg"):
        old.unlink()

    pdf_path = build_pdf(project, project_dir, settings, "family", preview=True)
    unreviewed = needs_review(project)
    names = []
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        for index in range(len(document)):
            image = document[index].render(scale=PREVIEW_DPI / 72).to_pil().convert("RGB")
            if unreviewed:
                _stamp(image)
            name = f"page-{index + 1:02d}.jpg"
            image.save(folder / name, "JPEG", quality=88)
            names.append(name)
    finally:
        document.close()
    return {"pages": names, "reviewed": not unreviewed}


def preview_page_path(project_dir: Path, name: str) -> Path | None:
    if not PAGE_NAME.fullmatch(name):
        return None
    path = Path(project_dir) / "preview" / name
    return path if path.is_file() else None
