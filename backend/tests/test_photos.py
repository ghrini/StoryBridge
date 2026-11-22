import io

import pytest
from PIL import Image

from app.schemas import Chapter
from app.services import photos
from app.services.photos import (
    PhotoError, PhotoNotFound, forget_photo, photo_path, save_photo, set_chapter_photo, set_cover_photo,
)
from app.services.storage import ProjectStore


def image_bytes(size=(400, 300), fmt="PNG", exif_orientation=None) -> io.BytesIO:
    image = Image.new("RGB", size, (90, 140, 200))
    buffer = io.BytesIO()
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation  # Orientation tag, as phones write it
        image.save(buffer, fmt, exif=exif)
    else:
        image.save(buffer, fmt)
    buffer.seek(0)
    return buffer


@pytest.fixture
def setup(tmp_path):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="self_demo")
    project.chapters = [Chapter(id="ch1", title="One", clip_start=0, clip_end=1),
                        Chapter(id="ch2", title="Two", clip_start=1, clip_end=2)]
    return store, project


def test_a_photo_is_stored_as_a_jpeg_under_a_name_we_choose(setup):
    store, project = setup
    relative = save_photo(store, project, "../../evil name.png", image_bytes())
    assert relative.startswith("photos/") and relative.endswith(".jpg") and "evil" not in relative
    with Image.open(store.project_dir(project.id) / relative) as stored:
        assert stored.format == "JPEG" and stored.size == (400, 300)


def test_sideways_phone_photos_are_turned_upright(setup):
    store, project = setup
    relative = save_photo(store, project, "phone.jpg", image_bytes((200, 100), "JPEG", exif_orientation=6))
    with Image.open(store.project_dir(project.id) / relative) as stored:
        assert stored.size == (100, 200)


def test_huge_photos_are_scaled_down(setup):
    store, project = setup
    relative = save_photo(store, project, "big.png", image_bytes((5000, 2500)))
    with Image.open(store.project_dir(project.id) / relative) as stored:
        assert max(stored.size) == 4000


@pytest.mark.parametrize("name, data", [
    ("notes.txt", io.BytesIO(b"hello")),
    ("virus.exe", image_bytes()),
    ("fake.jpg", io.BytesIO(b"this is not a picture")),
])
def test_things_that_are_not_pictures_are_refused(setup, name, data):
    store, project = setup
    with pytest.raises(PhotoError):
        save_photo(store, project, name, data)


def test_too_large_uploads_are_refused(setup, monkeypatch):
    store, project = setup
    monkeypatch.setattr(photos, "MAX_UPLOAD_BYTES", 100)
    with pytest.raises(PhotoError, match="too large"):
        save_photo(store, project, "a.png", image_bytes())


@pytest.mark.parametrize("bad", ["../project.json", "x.jpg", "ABCDEF0123456789ABCDEF0123456789.jpg", "0" * 32 + ".png"])
def test_photo_names_from_urls_cannot_reach_other_files(setup, bad):
    store, project = setup
    with pytest.raises(PhotoNotFound):
        photo_path(store, project.id, bad)


def test_replacing_the_cover_deletes_the_old_picture(setup):
    store, project = setup
    first = save_photo(store, project, "a.png", image_bytes())
    set_cover_photo(store, project, first)
    second = save_photo(store, project, "b.png", image_bytes())
    set_cover_photo(store, project, second)
    assert not (store.project_dir(project.id) / first).exists()
    assert (store.project_dir(project.id) / second).exists()


def test_a_picture_still_used_elsewhere_is_kept(setup):
    store, project = setup
    shared = save_photo(store, project, "a.png", image_bytes())
    project.cover_photo = shared
    set_chapter_photo(store, project, "ch1", shared)
    set_chapter_photo(store, project, "ch1", None)
    assert (store.project_dir(project.id) / shared).exists()  # the cover still uses it
    forget_photo(store, project, shared)
    assert (store.project_dir(project.id) / shared).exists()


def test_chapter_photos_and_captions(setup):
    store, project = setup
    relative = save_photo(store, project, "a.png", image_bytes())
    set_chapter_photo(store, project, "ch2", relative)
    project.chapters[1].photo_caption = "A caption"
    assert project.chapters[1].photo_file == relative
    set_chapter_photo(store, project, "ch2", None)
    assert project.chapters[1].photo_caption is None
    with pytest.raises(PhotoNotFound):
        set_chapter_photo(store, project, "ch9", relative)


