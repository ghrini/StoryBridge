"""Turn a finished book PDF into one picture per page, for photo-book services that build books from photos
(each 8 x 8 inch page becomes a 2400 x 2400 pixel image at 300 dpi)."""
import io
import zipfile
from pathlib import Path

import pypdfium2 as pdfium

README = """StoryBridge book pages
======================
Each picture is one finished 8 x 8 inch page at 300 dpi (2400 x 2400 pixels).

To make a printed photo book from these: choose an 8 x 8 inch book in your photo-book
service's editor, use a full-page photo layout, and place the pages in order (page-01, page-02, ...).

These pages have no QR codes: the voice codes only work on the home Wi-Fi of the StoryBridge computer.
"""


def page_images_zip(pdf_path: Path, dpi: int = 300) -> bytes:
    document = pdfium.PdfDocument(str(pdf_path))
    buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:  # JPEGs are already compressed
            archive.writestr("README.txt", README)
            for index in range(len(document)):
                image = document[index].render(scale=dpi / 72).to_pil().convert("RGB")
                out = io.BytesIO()
                image.save(out, "JPEG", quality=92, dpi=(dpi, dpi))
                archive.writestr(f"page-{index + 1:02d}.jpg", out.getvalue())
    finally:
        document.close()
    return buffer.getvalue()
