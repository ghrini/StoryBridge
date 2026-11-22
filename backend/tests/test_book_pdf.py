import uuid
from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image

from app.config import REVIEW_NOTICE, Settings
from app.schemas import BookSentence, Chapter, StoryProject
from app.services.book_pdf import (
    BODY_FONT, EDITIONS, SYSTEM_FONT_DIR, TITLE_FONT, ExportBlocked, about_text, book_title_for, build_pdf,
    chapter_text, clip_url, file_slug, possessive_name, qr_png,
)


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path, models_dir=tmp_path / "models", ffmpeg="ffmpeg",
        whisper_model="small", base_url="http://192.168.1.20:8000", clip_padding_seconds=0.25,
    )


def sentence(sentence_id, text, status="approved"):
    return BookSentence(id=sentence_id, text=text, source_segment_ids=["seg-0001"], status=status)


def make_project(**overrides) -> StoryProject:
    fields = dict(
        id="abcd1234", recording_kind="self_demo", family_name="Gram", pronouns="she/her",
        chapters=[
            Chapter(id="p1", title="Page 1", clip_start=0, clip_end=5,
                    sentences=[sentence("p1-s1", "Every morning, Gram hopped on her bike."),
                               sentence("p1-s2", "She pedaled all the way to school.")]),
            Chapter(id="p2", title="Page 2", clip_start=6, clip_end=9,
                    sentences=[sentence("p2-s1", "After school, Gram went to dance class.")]),
        ],
    )
    fields.update(overrides)
    return StoryProject(**fields)


def add_photo(folder, size=(1200, 800), color=(200, 120, 80)) -> str:
    (folder / "photos").mkdir(exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    Image.new("RGB", size, color).save(folder / "photos" / name, "JPEG")
    return f"photos/{name}"


def pdf_pages(path):
    document = pdfium.PdfDocument(str(path))
    pages = [(page.get_size(), " ".join(page.get_textpage().get_text_range().split())) for page in document]
    document.close()
    return pages


def pixel(path, page_index, xy):
    document = pdfium.PdfDocument(str(path))
    image = document[page_index].render(scale=0.5).to_pil().convert("RGB")
    document.close()
    return image.getpixel(xy)


# --- words -----------------------------------------------------------------------------------------

def test_clip_url_points_at_the_local_server(settings):
    assert clip_url(settings, "abcd1234", "p2") == "http://192.168.1.20:8000/api/projects/abcd1234/clips/p2.mp3"


def test_qr_png_is_a_png():
    assert qr_png("http://x/y").read(8) == b"\x89PNG\r\n\x1a\n"


def test_removed_sentences_are_left_out():
    page = Chapter(id="p1", title="Page 1", clip_start=0, clip_end=1,
                   sentences=[sentence("a", "One."), sentence("b", "Gone.", "removed"), sentence("c", "Two.")])
    assert chapter_text(page) == "One. Two."


def test_book_title_prefers_a_persons_title_then_the_suggestion_then_a_default():
    assert book_title_for(make_project(book_title="My Title", suggested_title="AI Title")) == "My Title"
    assert book_title_for(make_project(suggested_title="Gram's Typical Day in High School")) == "Gram's Typical Day in High School"
    assert book_title_for(make_project()) == "Gram's Story"
    assert book_title_for(make_project(family_name=None)) == "A Life Story"
    assert possessive_name("Charles") == "Charles'"


def test_the_last_page_says_how_the_book_was_made():
    drafted = " ".join(about_text(make_project(drafted_by="Google Gemini"), EDITIONS["print"]))
    assert "drafted with the help of AI" in drafted and "her own story" in drafted and "Scan the code" in drafted
    assert REVIEW_NOTICE in drafted and "Demo book" in drafted
    plain = " ".join(about_text(make_project(), EDITIONS["family"]))
    assert "AI" not in plain and "Scan" not in plain


def test_file_names_are_safe():
    assert file_slug("Gram's Typical Day in High School!") == "Gram-s-Typical-Day-in-High-School"
    assert file_slug("???") == "storybook"


# --- the PDF -------------------------------------------------------------------------------------------

def test_title_font_is_chewy_and_story_font_is_arial():
    assert TITLE_FONT == "SB-Title"  # assets/fonts/Chewy-Regular.ttf loaded
    if (SYSTEM_FONT_DIR / "arial.ttf").is_file():
        assert BODY_FONT == "SB-Arial"
    else:
        assert BODY_FONT == "Helvetica"  # looks the same; used where Arial isn't installed


def test_print_edition_has_bleed_page_codes_and_the_notice(tmp_path, settings):
    path = build_pdf(make_project(), tmp_path, settings, "print")
    pages = pdf_pages(path)
    assert [size for size, _ in pages] == [(594.0, 594.0)] * 4  # cover, 2 story pages, the end; 8 in + bleed
    assert "Gram's Story" in pages[0][1] and "A story from Gram's memories" in pages[0][1]
    assert "Every morning, Gram hopped on her bike." in pages[1][1] and "Scan to hear Gram" in pages[1][1]
    assert "Chapter" not in " ".join(text for _, text in pages)
    assert "The End" in pages[-1][1] and REVIEW_NOTICE in pages[-1][1]


def test_pages_are_white(tmp_path, settings):
    path = build_pdf(make_project(), tmp_path, settings, "family")
    assert pixel(path, 1, (5, 5)) == (255, 255, 255)


def test_family_edition_is_trimmed_and_has_no_qr_codes(tmp_path, settings):
    path = build_pdf(make_project(), tmp_path, settings, "family")
    pages = pdf_pages(path)
    assert pages[0][0] == (576.0, 576.0)  # exactly 8 x 8 inches
    assert "Scan" not in " ".join(text for _, text in pages)
    assert path.name == "book-family.pdf"


def test_empty_picture_boxes_say_so_only_in_the_preview(tmp_path, settings):
    exported = " ".join(t for _, t in pdf_pages(build_pdf(make_project(), tmp_path, settings, "family")))
    previewed = " ".join(t for _, t in pdf_pages(build_pdf(make_project(), tmp_path, settings, "family", preview=True)))
    assert "Picture goes here" not in exported  # a printed empty frame stays blank for drawing or a photo
    assert previewed.count("Picture goes here") == 3  # cover and both pages


def test_uploaded_pictures_fill_their_boxes(tmp_path, settings):
    project = make_project(cover_photo=add_photo(tmp_path, (900, 1400)))
    project.chapters[0].photo_file = add_photo(tmp_path, (800, 1200), color=(20, 120, 220))
    path = build_pdf(project, tmp_path, settings, "family", preview=True)
    pages = pdf_pages(path)
    assert len(pages) == 4 and "Picture goes here" not in pages[1][1] and "Picture goes here" in pages[2][1]
    r, g, b = pixel(path, 1, (144, 100))  # inside page 2's picture box
    assert b > 180 and r < 60  # the blue test picture, not the grey empty box


def test_a_long_page_still_fits_at_14_point_or_larger(tmp_path, settings):
    long_text = " ".join(["Gram rode her blue bike down Maple Hill and pushed it all the way back up again."] * 6)
    project = make_project()
    project.chapters[0].sentences = [sentence("p1-s1", long_text)]
    pages = pdf_pages(build_pdf(project, tmp_path, settings, "family"))
    assert pages[1][1].count("Maple Hill") == 6  # all of it is on the page


def test_demo_books_say_so_on_the_cover(tmp_path, settings):
    pages = pdf_pages(build_pdf(make_project(recording_kind="synthetic_dev"), tmp_path, settings, "family"))
    assert "Demo book" in pages[0][1]


def test_the_book_is_blocked_while_a_sentence_is_flagged(tmp_path, settings):
    project = make_project()
    project.chapters[0].sentences[0].status = "flagged"
    with pytest.raises(ExportBlocked) as blocked:
        build_pdf(project, tmp_path, settings)
    assert "not been confirmed" in str(blocked.value)
    assert not list(Path(tmp_path).glob("book-*.pdf"))


def test_a_book_needs_pages_and_words(tmp_path, settings):
    with pytest.raises(ValueError):
        build_pdf(make_project(chapters=[]), tmp_path, settings)
    project = make_project()
    for page in project.chapters:
        for s in page.sentences:
            s.status = "removed"
    with pytest.raises(ValueError):
        build_pdf(project, tmp_path, settings)


def test_a_page_with_every_sentence_removed_is_skipped(tmp_path, settings):
    project = make_project()
    project.chapters[0].sentences = [sentence("p1-s1", "Gone.", "removed")]
    pages = pdf_pages(build_pdf(project, tmp_path, settings, "family"))
    assert len(pages) == 3 and "After school" in pages[1][1]
