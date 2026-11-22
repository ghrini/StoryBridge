"""The picture book: square 8 x 8 inch white pages, each with a picture box and a few lines of story.

Two editions of the same book:
- "print": 1/8 inch bleed on every side (what print services ask for) and a small QR code on each page
  that plays the storyteller's voice from this computer.
- "family": trimmed pages without QR codes (they only work on the home Wi-Fi), for sending to family.
An empty picture box prints as a frame, so the family can glue in a photo or draw a picture.
"""
import io
import os
import re
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import qrcode
from PIL import Image, ImageOps
from qrcode.constants import ERROR_CORRECT_M
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Paragraph

from ..config import REPO_ROOT, REVIEW_NOTICE, Settings
from ..schemas import Chapter, StoryProject

# --- look ------------------------------------------------------------------------------------
PAPER = white
INK = HexColor("#1F1F1F")
GRAY = HexColor("#6B6B6B")
BOX = HexColor("#F2F2F2")
BOX_LINE = HexColor("#B5B5B5")

TRIM = 8 * inch               # finished page size
BLEED = 0.125 * inch          # extra edge that print services trim off
SAFE = 0.6 * inch             # words and pictures stay this far inside the trimmed edge
BODY_SIZES = (17, 16, 15, 14)  # story text shrinks to fit, never below 14 pt (for older readers)
PICTURE_H = 4.4 * inch
MIN_PICTURE_H = 2.4 * inch
CORNER = 10

DEMO_LABELS = {
    "synthetic_dev": "Demo book: a computer voice reading a fictional story, not a real person.",
    "self_demo": "Demo book made from the student's own demo recording.",
}
POSSESSIVE = {"she/her": "her", "he/him": "his", "they/them": "their"}


@dataclass(frozen=True)
class Edition:
    name: str
    bleed: float
    qr: bool
    dpi: int  # resolution pictures are prepared at


EDITIONS = {
    "print": Edition("print", BLEED, True, 300),
    "family": Edition("family", 0, False, 150),
}

FONT_DIR = REPO_ROOT / "assets" / "fonts"
SYSTEM_FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def _register(name: str, path: Path) -> bool:
    try:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(path)))
        return True
    except Exception:
        return False


# Chewy (bundled, Apache-2.0) for titles; Arial from Windows for everything else. Helvetica, which looks the
# same as Arial, is the fallback on computers without Arial (Arial's license doesn't allow bundling it).
TITLE_FONT = "SB-Title" if _register("SB-Title", FONT_DIR / "Chewy-Regular.ttf") else "Helvetica-Bold"
BODY_FONT = "SB-Arial" if _register("SB-Arial", SYSTEM_FONT_DIR / "arial.ttf") else "Helvetica"
ITALIC_FONT = "SB-Arial-Italic" if _register("SB-Arial-Italic", SYSTEM_FONT_DIR / "ariali.ttf") else "Helvetica-Oblique"


def _style(font: str, size: float, color=INK, leading: float = 1.4) -> ParagraphStyle:
    return ParagraphStyle(f"{font}-{size}", fontName=font, fontSize=size, leading=size * leading,
                          alignment=TA_CENTER, textColor=color)


class ExportBlocked(Exception):
    """The book cannot be exported yet (for example, a sentence is still flagged for review)."""


# --- words -----------------------------------------------------------------------------------

def display_name(project: StoryProject) -> str:
    return (project.family_name or project.storyteller_name or "").strip()


def possessive_name(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def book_title_for(project: StoryProject) -> str:
    for title in (project.book_title, project.suggested_title):
        if title and title.strip():
            return title.strip()
    name = display_name(project)
    return f"{possessive_name(name)} Story" if name else "A Life Story"


def chapter_text(chapter: Chapter) -> str:
    """A page's words as shown in the book: removed sentences are left out."""
    return " ".join(s.text.strip() for s in chapter.sentences if s.status != "removed")


def about_text(project: StoryProject, edition: Edition) -> list[str]:
    """The small print on the last page: how the book was made, and the review notice."""
    name = display_name(project) or "the storyteller"
    their = POSSESSIVE.get(project.pronouns or "", "their")
    if project.drafted_by:
        lines = [f"This book was written from a recording of {name} telling {their} own story. "
                 "The words were drafted with the help of AI, and a person read the whole story and confirmed it."]
    else:
        lines = [f"The words in this book come from a recording of {name} telling {their} own story."]
    if edition.qr:
        lines.append(f"Scan the code on a page with a phone to hear that part in {possessive_name(name)} own voice "
                     "(it works while the StoryBridge computer is on the same Wi-Fi).")
    lines.append(REVIEW_NOTICE)
    if project.recording_kind in DEMO_LABELS:
        lines.append(DEMO_LABELS[project.recording_kind])
    lines.append("Made with StoryBridge, a SmileCard project.")
    return lines


def clip_url(settings: Settings, project_id: str, chapter_id: str) -> str:
    return f"{settings.base_url}/api/projects/{project_id}/clips/{chapter_id}.mp3"


def qr_png(url: str) -> io.BytesIO:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer)
    buffer.seek(0)
    return buffer


def file_slug(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")[:60] or "storybook"


# --- pictures --------------------------------------------------------------------------------

def cropped_image(path: Path, width_pt: float, height_pt: float, dpi: int) -> ImageReader:
    """Crop the picture to fill the box (like a photo book does) and size it for the edition."""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    ratio = width_pt / height_pt
    w, h = image.size
    if w / h > ratio:  # too wide: trim the sides
        new_w = max(1, int(h * ratio))
        left = (w - new_w) // 2
        image = image.crop((left, 0, left + new_w, h))
    else:  # too tall: trim top and bottom
        new_h = max(1, int(w / ratio))
        top = (h - new_h) // 2
        image = image.crop((0, top, w, top + new_h))
    longest = int(max(width_pt, height_pt) / 72 * dpi)
    image.thumbnail((longest, longest))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=88)
    buffer.seek(0)
    return ImageReader(buffer)


def draw_picture_box(c, x, y, w, h, photo: Path | None, edition: Edition, preview: bool) -> None:
    """The picture with rounded corners, or an empty frame where a picture can go."""
    c.saveState()
    if photo is not None:
        path = c.beginPath()
        path.roundRect(x, y, w, h, CORNER)
        c.clipPath(path, stroke=0, fill=0)
        c.drawImage(cropped_image(photo, w, h, edition.dpi), x, y, w, h)
    else:
        c.setFillColor(BOX)
        c.setStrokeColor(BOX_LINE)
        c.setLineWidth(1)
        c.setDash(6, 4)
        c.roundRect(x, y, w, h, CORNER, stroke=1, fill=1)
        if preview:  # only on screen; a printed empty frame stays blank for drawing or gluing in a photo
            c.setFillColor(GRAY)
            c.setFont(BODY_FONT, 14)
            c.drawCentredString(x + w / 2, y + h / 2 - 5, "Picture goes here")
    c.restoreState()


# --- pages -----------------------------------------------------------------------------------

def _blank_page(c, size: float) -> None:
    c.setFillColor(PAPER)
    c.rect(0, 0, size, size, fill=1, stroke=0)


def _fitting_text(text: str, width: float, max_height: float) -> tuple[Paragraph, float]:
    """The story text at the largest size (17 pt down to 14 pt) that fits the space."""
    for size in BODY_SIZES:
        paragraph = Paragraph(escape(text), _style(BODY_FONT, size))
        _, height = paragraph.wrap(width, 10_000)
        if height <= max_height:
            break
    return paragraph, height


def paint_cover(c, project: StoryProject, edition: Edition, project_dir: Path, preview: bool) -> None:
    size = TRIM + 2 * edition.bleed
    _blank_page(c, size)
    b = edition.bleed
    left, width, top, bottom = b + SAFE, TRIM - 2 * SAFE, b + TRIM - SAFE, b + SAFE

    title = Paragraph(escape(book_title_for(project)), _style(TITLE_FONT, 46, leading=1.15))
    _, title_h = title.wrap(width, size)
    title.drawOn(c, left, top - title_h)

    name = display_name(project)
    subtitle = Paragraph(escape(f"A story from {possessive_name(name)} memories" if name else "A story from a lifetime of memories"),
                         _style(BODY_FONT, 16, color=GRAY))
    _, sub_h = subtitle.wrap(width, size)
    subtitle.drawOn(c, left, top - title_h - 8 - sub_h)

    label_h = 0
    if project.recording_kind in DEMO_LABELS:
        label = Paragraph(escape(DEMO_LABELS[project.recording_kind]), _style(ITALIC_FONT, 11, color=GRAY))
        _, label_h = label.wrap(width, size)
        label.drawOn(c, left, bottom)

    box_top = top - title_h - 8 - sub_h - 0.3 * inch
    box_bottom = bottom + (label_h + 0.25 * inch if label_h else 0)
    box_w = width * 0.88
    photo = Path(project_dir) / project.cover_photo if project.cover_photo else None
    draw_picture_box(c, left + (width - box_w) / 2, box_bottom, box_w, box_top - box_bottom, photo, edition, preview)


def paint_story_page(c, project, chapter, edition, settings, project_dir: Path, preview: bool) -> None:
    size = TRIM + 2 * edition.bleed
    _blank_page(c, size)
    b = edition.bleed
    left, width, top = b + SAFE, TRIM - 2 * SAFE, b + TRIM - SAFE
    bottom = b + SAFE + (0.55 * inch if edition.qr else 0.15 * inch)  # room for the page number (and QR code)
    gap = 0.3 * inch
    room = top - bottom

    text = chapter_text(chapter)
    paragraph, text_h = _fitting_text(text, width, room - gap - PICTURE_H)
    picture_h = PICTURE_H if text_h <= room - gap - PICTURE_H else max(MIN_PICTURE_H, room - gap - text_h)
    if picture_h + gap + text_h > room:  # an unusually long page: give the words the whole page
        picture_h = 0
        paragraph, text_h = _fitting_text(text, width, room)

    if picture_h:
        photo = Path(project_dir) / chapter.photo_file if chapter.photo_file else None
        draw_picture_box(c, left, top - picture_h, width, picture_h, photo, edition, preview)
    text_top = top - picture_h - (gap if picture_h else 0)
    paragraph.drawOn(c, left, text_top - text_h)

    c.setFont(BODY_FONT, 11)
    c.setFillColor(GRAY)
    c.drawCentredString(size / 2, b + 0.4 * inch, str(c.getPageNumber()))

    if edition.qr and chapter.segment_ids:  # a page written only from the family's message has no voice clip
        qr_size = 0.62 * inch
        qr_x, qr_y = b + TRIM - SAFE - qr_size, b + 0.3 * inch
        c.drawImage(ImageReader(qr_png(clip_url(settings, project.id, chapter.id))), qr_x, qr_y, qr_size, qr_size)
        c.setFont(ITALIC_FONT, 9)
        name = display_name(project)
        c.drawRightString(qr_x - 5, qr_y + qr_size / 2 - 3, f"Scan to hear {name}" if name else "Scan to hear the voice")


def paint_photo_page(c, path: Path, caption: str | None, edition: Edition) -> None:
    """A full-page photo (kept for books that already have one)."""
    size = TRIM + 2 * edition.bleed
    _blank_page(c, size)
    c.drawImage(cropped_image(path, size, size, edition.dpi), 0, 0, size, size)
    if caption:
        band_h = edition.bleed + 0.8 * inch
        c.saveState()
        c.setFillColor(white)
        c.setFillAlpha(0.88)
        c.rect(0, 0, size, band_h, fill=1, stroke=0)
        c.restoreState()
        text = Paragraph(escape(caption), _style(ITALIC_FONT, 14))
        _, text_h = text.wrap(TRIM - 2 * SAFE, band_h)
        text.drawOn(c, edition.bleed + SAFE, edition.bleed + (0.8 * inch - text_h) / 2)


def paint_end(c, project: StoryProject, edition: Edition) -> None:
    size = TRIM + 2 * edition.bleed
    _blank_page(c, size)
    b = edition.bleed
    left, width = b + SAFE, TRIM - 2 * SAFE

    the_end = Paragraph("The End", _style(TITLE_FONT, 54, leading=1.1))
    _, end_h = the_end.wrap(width, size)
    the_end.drawOn(c, left, b + TRIM * 0.62)

    notes = [Paragraph(escape(line), _style(BODY_FONT, 11, color=GRAY, leading=1.35)) for line in about_text(project, edition)]
    inner = width - 0.5 * inch
    heights = [p.wrap(inner, size)[1] for p in notes]
    box_h = sum(heights) + 6 * (len(notes) - 1) + 0.4 * inch
    box_y = b + SAFE
    c.setFillColor(BOX)
    c.roundRect(left, box_y, width, box_h, CORNER, stroke=0, fill=1)
    y = box_y + box_h - 0.2 * inch
    for paragraph, height in zip(notes, heights):
        y -= height
        paragraph.drawOn(c, left + 0.25 * inch, y)
        y -= 6


def check_ready(project: StoryProject, allow_unreviewed: bool = False) -> None:
    """Exports need a person to have confirmed the story. Only the stamped in-app preview may skip that rule."""
    if not project.chapters:
        raise ValueError("Make the storybook first.")
    flagged = [s.id for c in project.chapters for s in c.sentences if s.status == "flagged"]
    if flagged and not allow_unreviewed:
        raise ExportBlocked(
            f"The story has not been confirmed yet ({len(flagged)} new or changed sentence(s) not read). "
            "Read it, then press \"The story is right\"."
        )
    if not any(chapter_text(c) for c in project.chapters):
        raise ValueError("The book has no sentences left.")


def build_pdf(
    project: StoryProject, project_dir: Path, settings: Settings, edition: str = "print", preview: bool = False
) -> Path:
    """Write book-<edition>.pdf into the project folder and return its path.

    preview=True is only for the in-app page flipper: it may include unreviewed sentences, shows
    "Picture goes here" in empty boxes, is written to preview/book-preview.pdf, and is never offered for download."""
    check_ready(project, allow_unreviewed=preview)
    chosen = EDITIONS[edition]
    size = TRIM + 2 * chosen.bleed
    project_dir = Path(project_dir)
    if preview:
        (project_dir / "preview").mkdir(parents=True, exist_ok=True)
        destination = project_dir / "preview" / "book-preview.pdf"
    else:
        destination = project_dir / f"book-{chosen.name}.pdf"

    c = pdf_canvas.Canvas(str(destination), pagesize=(size, size))
    c.setTitle(book_title_for(project))
    c.setAuthor("StoryBridge")

    paint_cover(c, project, chosen, project_dir, preview)
    c.showPage()

    pages_after = {}
    for photo_page in project.photo_pages:
        pages_after.setdefault(photo_page.after_chapter_id, []).append(photo_page)

    def photo_pages(after_id):
        for photo_page in pages_after.get(after_id, []):
            paint_photo_page(c, project_dir / photo_page.photo_file, photo_page.caption, chosen)
            c.showPage()

    photo_pages(None)
    for chapter in project.chapters:
        if chapter_text(chapter):
            paint_story_page(c, project, chapter, chosen, settings, project_dir, preview)
            c.showPage()
        photo_pages(chapter.id)

    paint_end(c, project, chosen)
    c.showPage()
    c.save()
    return destination
