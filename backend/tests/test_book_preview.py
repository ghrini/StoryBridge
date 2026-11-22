import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from app.services.book_preview import STAMP_COLOR, build_preview, preview_page_path
from test_api import LOCAL, PHONE, drafted_project, new_demo_project, reviewed_book
from test_book_pdf import make_project


@pytest.fixture
def settings(tmp_path):
    from app.config import Settings

    return Settings(
        data_dir=tmp_path, models_dir=tmp_path / "models", ffmpeg="ffmpeg",
        whisper_model="small", base_url="http://192.168.1.20:8000", clip_padding_seconds=0.25,
    )


def top_left(path):
    with Image.open(path) as image:
        return image.convert("RGB").getpixel((5, 5))


def test_a_reviewed_book_previews_without_a_stamp(tmp_path, settings):
    result = build_preview(make_project(), tmp_path, settings)
    assert result["reviewed"] is True and result["pages"][0] == "page-01.jpg" and len(result["pages"]) == 4
    assert top_left(tmp_path / "preview" / "page-01.jpg") != STAMP_COLOR


def test_an_unreviewed_book_can_be_previewed_but_every_page_is_stamped(tmp_path, settings):
    project = make_project()
    project.chapters[0].sentences[0].status = "flagged"
    result = build_preview(project, tmp_path, settings)
    assert result["reviewed"] is False
    for name in result["pages"]:
        r, g, b = top_left(tmp_path / "preview" / name)
        assert abs(r - STAMP_COLOR[0]) < 12 and abs(g - STAMP_COLOR[1]) < 12 and abs(b - STAMP_COLOR[2]) < 12
    assert not (tmp_path / "book-family.pdf").exists()  # a preview is never an export


def test_old_preview_pages_are_cleared(tmp_path, settings):
    (tmp_path / "preview").mkdir()
    (tmp_path / "preview" / "page-99.jpg").write_bytes(b"old")
    build_preview(make_project(), tmp_path, settings)
    assert not (tmp_path / "preview" / "page-99.jpg").exists()


@pytest.mark.parametrize("bad", ["../project.json", "page-1.jpg", "page-01.png", "book-preview.pdf"])
def test_only_preview_pictures_can_be_fetched(tmp_path, settings, bad):
    build_preview(make_project(), tmp_path, settings)
    assert preview_page_path(tmp_path, bad) is None
    assert preview_page_path(tmp_path, "page-01.jpg") is not None


def test_preview_api_before_and_after_review(settings):
    client = TestClient(create_app(settings), client=LOCAL)
    project_id = drafted_project(client, settings)["id"]
    before = client.get(f"/api/projects/{project_id}/book-preview").json()
    assert before["reviewed"] is False and before["pages"][0].endswith("/preview/page-01.jpg")
    page = client.get(before["pages"][0])
    assert page.status_code == 200 and page.headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/projects/{project_id}/book.pdf?edition=family").status_code == 409  # still locked
    assert client.get(f"/api/projects/{project_id}/preview/..%2Fproject.json").status_code == 404

    reviewed_id = reviewed_book(client, settings)
    assert client.get(f"/api/projects/{reviewed_id}/book-preview").json()["reviewed"] is True


def test_preview_needs_chapters_and_is_for_this_computer_only(settings):
    local = TestClient(create_app(settings), client=LOCAL)
    phone = TestClient(create_app(settings), client=PHONE)
    project_id = new_demo_project(local)
    assert local.get(f"/api/projects/{project_id}/book-preview").status_code == 409
    assert phone.get(f"/api/projects/{project_id}/book-preview").status_code == 403
    assert phone.get(f"/api/projects/{project_id}/preview/page-01.jpg").status_code == 403
