import io
import json
import shutil
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import REVIEW_NOTICE, Settings
from app.main import create_app
from app.schemas import TranscriptSegment
from app.services.storage import ProjectStore
from test_photos import image_bytes
from test_record import sine_wav_bytes
from test_schemas import make_consent

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not on PATH")
LOCAL = ("127.0.0.1", 50000)
PHONE = ("192.168.1.9", 50000)

SAVED_DRAFT = {
    "drafted_by": "Test AI, saved draft",
    "book_title": "Gram's Day",
    "pages": [
        {"photo_idea": "a blue bike", "sentences": [
            {"text": "Gram rode her bike to school.", "source_segment_ids": ["seg-0001"]},
            {"text": "It was blue.", "source_segment_ids": ["seg-0002"]}]},
        {"photo_idea": "a typing class", "sentences": [
            {"text": "Then she went to typing class.", "source_segment_ids": ["seg-0009"]}]},
        {"sentences": [{"text": "Lunch was on the steps.", "source_segment_ids": ["seg-0017"]}]},
    ],
}


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path, models_dir=tmp_path / "models", ffmpeg=shutil.which("ffmpeg") or "ffmpeg",
        whisper_model="small", base_url="http://192.168.1.20:8000", clip_padding_seconds=0.25,
    )


@pytest.fixture
def client(settings):
    return TestClient(create_app(settings), client=LOCAL)


def new_demo_project(client) -> str:
    response = client.post("/api/projects", json={"storyteller_name": "Pat", "recording_kind": "synthetic_dev"})
    assert response.status_code == 200
    return response.json()["id"]


def give_fake_transcript(settings, project_id, count=22):
    """Skip real Whisper: write a transcript straight into the project."""
    store = ProjectStore(settings.data_dir)
    project = store.load(project_id)
    project.transcript = [
        TranscriptSegment(id=f"seg-{i + 1:04d}", text=f"Line {i + 1}.", start=i * 1.5, end=i * 1.5 + 1.2)
        for i in range(count)
    ]
    store.save(project)


def drafted_project(client, settings) -> dict:
    """A storybook made from a saved AI draft: 3 pages, 4 sentences that need review (no key, no internet)."""
    project_id = new_demo_project(client)
    give_fake_transcript(settings, project_id)
    (settings.data_dir / "projects" / project_id / "ai_draft.json").write_text(json.dumps(SAVED_DRAFT), encoding="utf-8")
    response = client.post(f"/api/projects/{project_id}/draft")
    assert response.status_code == 200
    return response.json()


def reviewed_book(client, settings) -> str:
    project = drafted_project(client, settings)
    for page in project["chapters"]:
        for sentence in page["sentences"]:
            client.patch(f"/api/projects/{project['id']}/sentences/{sentence['id']}", json={"status": "approved"})
    return project["id"]


# --- basics ------------------------------------------------------------------------------------------

def test_config_gives_the_review_notice_and_qr_base_url(client, settings):
    config = client.get("/api/config").json()
    assert config["review_notice"] == REVIEW_NOTICE and config["base_url"] == settings.base_url


def test_storyteller_project_without_consent_is_rejected(client):
    assert client.post("/api/projects", json={"recording_kind": "storyteller"}).status_code == 422


def test_upload_is_refused_without_recording_consent(client):
    consent = make_consent(agreed_recording=False).model_dump(mode="json")
    project_id = client.post("/api/projects", json={"recording_kind": "storyteller", "consent": consent}).json()["id"]
    response = client.post(f"/api/projects/{project_id}/audio", files={"file": ("a.wav", sine_wav_bytes())})
    assert response.status_code == 403


@needs_ffmpeg
def test_upload_rejects_unknown_file_type(client):
    project_id = new_demo_project(client)
    assert client.post(f"/api/projects/{project_id}/audio", files={"file": ("a.exe", b"x")}).status_code == 400


def test_unknown_project_is_404_and_bad_ids_are_not_traversal(client):
    assert client.get("/api/projects/abcd1234").status_code == 404
    assert client.get("/api/projects/..%2F..%2Fetc").status_code == 404


def test_book_details_can_be_set_and_cleared(client):
    project_id = new_demo_project(client)
    updated = client.patch(f"/api/projects/{project_id}",
                           json={"family_name": " Gram ", "pronouns": "she/her", "book_title": "Gram's Day"}).json()
    assert (updated["family_name"], updated["pronouns"], updated["book_title"]) == ("Gram", "she/her", "Gram's Day")
    cleared = client.patch(f"/api/projects/{project_id}", json={"book_title": ""}).json()
    assert cleared["book_title"] is None and cleared["family_name"] == "Gram"
    assert client.patch(f"/api/projects/{project_id}", json={"pronouns": "it/its"}).status_code == 422


# --- making the storybook --------------------------------------------------------------------------------

def test_making_the_storybook_needs_a_transcript(client):
    project_id = new_demo_project(client)
    assert client.post(f"/api/projects/{project_id}/draft").status_code == 422


def test_without_ai_or_a_saved_draft_the_book_uses_their_own_words(client, settings):
    project_id = new_demo_project(client)
    give_fake_transcript(settings, project_id, count=7)
    made = client.post(f"/api/projects/{project_id}/draft").json()
    assert [p["id"] for p in made["chapters"]] == ["p1", "p2", "p3"]
    assert made["chapters"][0]["sentences"][0]["text"] == "Line 1." and "own words" in made["warnings"][0]["message"]


def test_a_drafted_story_blocks_the_book_until_a_person_confirms_it(client, settings):
    project = drafted_project(client, settings)
    project_id = project["id"]
    sentences = [s for page in project["chapters"] for s in page["sentences"]]
    assert len(project["chapters"]) == 3 and len(sentences) == 4 and all(s["status"] == "flagged" for s in sentences)
    assert project["suggested_title"] == "Gram's Day" and project["chapters"][0]["photo_idea"] == "a blue bike"

    blocked = client.get(f"/api/projects/{project_id}/book.pdf?edition=family")
    assert blocked.status_code == 409 and "not been confirmed" in blocked.json()["detail"]
    assert client.get(f"/api/projects/{project_id}/book-pages.zip").status_code == 409

    confirmed = client.post(f"/api/projects/{project_id}/confirm")
    assert confirmed.status_code == 200
    assert all(s["status"] == "approved" for page in confirmed.json()["chapters"] for s in page["sentences"])
    assert client.get(f"/api/projects/{project_id}/book.pdf?edition=family").status_code == 200


def test_sentences_can_still_be_approved_one_by_one(client, settings):
    project = drafted_project(client, settings)
    for page in project["chapters"]:
        for sentence in page["sentences"]:
            client.patch(f"/api/projects/{project['id']}/sentences/{sentence['id']}", json={"status": "approved"})
    assert client.get(f"/api/projects/{project['id']}/book.pdf?edition=family").status_code == 200


def test_confirming_needs_a_book(client):
    assert client.post(f"/api/projects/{new_demo_project(client)}/confirm").status_code == 422


def test_ask_for_changes_says_when_the_ai_cannot_be_used(client, settings):
    project = drafted_project(client, settings)  # the test settings have no Gemini key
    helper = client.get(f"/api/projects/{project['id']}/ai-helper").json()
    assert helper == {"available": False, "reason": "No Gemini API key is set."}

    refused = client.post(f"/api/projects/{project['id']}/revise", json={"request": "Make page 2 shorter."})
    assert refused.status_code == 409 and "by hand" in refused.json()["detail"]
    assert client.get(f"/api/projects/{project['id']}").json()["chapters"] == project["chapters"]  # nothing changed


def test_ask_for_changes_with_the_ai(client, settings, monkeypatch):
    from app.providers.base import Revision
    from app.services import drafting

    project = drafted_project(client, settings)
    client.patch(f"/api/projects/{project['id']}", json={"family_name": "Gram", "pronouns": "she/her"})
    client.post(f"/api/projects/{project['id']}/confirm")
    first = project["chapters"][0]["sentences"]
    asked = []

    class FakeGemini:
        name = "Fake AI"

        def revise_story(self, current, request):
            asked.append(request)
            return Revision(reply="I changed page 2.", book_title="Gram's Day", pages=[
                {"from_page": "p1", "photo_idea": "a red bike",
                 "sentences": [{"text": first[0]["text"], "source_segment_ids": first[0]["source_segment_ids"]},
                               {"text": "Her bike was red.", "source_segment_ids": []}]},
                *({"from_page": page["id"], "photo_idea": page["photo_idea"],
                   "sentences": [{"text": s["text"], "source_segment_ids": s["source_segment_ids"]} for s in page["sentences"]]}
                  for page in project["chapters"][1:]),
            ])

    monkeypatch.setattr(drafting, "external_ai_block_reason", lambda *_: None)
    monkeypatch.setattr(drafting, "live_provider", lambda *_: FakeGemini())
    response = client.post(f"/api/projects/{project['id']}/revise", json={"request": "  Her bike was red, not blue.  "})
    assert response.status_code == 200, response.text
    body = response.json()
    assert asked == ["Her bike was red, not blue."]
    assert body["reply"] == "I changed page 2." and body["changed_pages"] == [2]
    page = body["project"]["chapters"][0]
    assert [s["status"] for s in page["sentences"]] == ["approved", "flagged"]  # only the new sentence needs reading
    assert page["photo_idea"] == "a red bike"
    assert client.get(f"/api/projects/{project['id']}/book.pdf?edition=family").status_code == 409

    client.post(f"/api/projects/{project['id']}/confirm")
    assert client.get(f"/api/projects/{project['id']}/book.pdf?edition=family").status_code == 200


def test_an_empty_change_request_is_refused(client, settings):
    project = drafted_project(client, settings)
    assert client.post(f"/api/projects/{project['id']}/revise", json={"request": "   "}).status_code == 422


def test_removing_a_sentence_also_counts_as_reviewing_it(client, settings):
    project = drafted_project(client, settings)
    for page in project["chapters"]:
        for sentence in page["sentences"]:
            body = {"status": "removed"} if sentence["id"] == "p1-s2" else {"status": "approved"}
            client.patch(f"/api/projects/{project['id']}/sentences/{sentence['id']}", json=body)
    assert client.get(f"/api/projects/{project['id']}/book.pdf?edition=family").status_code == 200


def test_editing_a_sentence_saves_the_new_wording_as_human_written(client, settings):
    project = drafted_project(client, settings)
    response = client.patch(f"/api/projects/{project['id']}/sentences/p1-s2", json={"text": "The bike was blue."})
    sentence = response.json()["chapters"][0]["sentences"][1]
    assert (sentence["text"], sentence["edit_type"], sentence["status"]) == ("The bike was blue.", "volunteer_caption", "approved")


def test_review_errors(client, settings):
    project = drafted_project(client, settings)
    base = f"/api/projects/{project['id']}/sentences"
    assert client.patch(f"{base}/p9-s9", json={"status": "approved"}).status_code == 404
    assert client.patch(f"{base}/p1-s1", json={"status": "maybe"}).status_code == 422
    assert client.patch(f"{base}/p1-s1", json={"text": "  "}).status_code == 422


def test_a_real_storyteller_without_outside_ai_consent_still_gets_a_book(client, settings):
    consent = make_consent().model_dump(mode="json")
    project_id = client.post("/api/projects", json={"recording_kind": "storyteller", "consent": consent}).json()["id"]
    give_fake_transcript(settings, project_id, count=4)
    made = client.post(f"/api/projects/{project_id}/draft").json()
    assert made["drafted_by"] is None and len(made["chapters"]) == 2


# --- pictures -----------------------------------------------------------------------------------------

def test_pictures_for_the_cover_and_each_page(client, settings):
    project_id = drafted_project(client, settings)["id"]
    base = f"/api/projects/{project_id}"
    cover = client.put(f"{base}/cover-photo", files={"file": ("cover.png", image_bytes())}).json()["cover_photo"]
    page = client.put(f"{base}/pages/p2/photo", files={"file": ("c.jpg", image_bytes(fmt="JPEG"))}).json()
    assert page["chapters"][1]["photo_file"].startswith("photos/")

    shown = client.get(f"{base}/{cover}")
    assert shown.status_code == 200 and shown.headers["content-type"] == "image/jpeg"
    assert client.put(f"{base}/cover-photo", files={"file": ("notes.txt", b"hi")}).status_code == 400
    assert client.put(f"{base}/pages/p9/photo", files={"file": ("c.png", image_bytes())}).status_code == 404

    assert client.delete(f"{base}/pages/p2/photo").json()["chapters"][1]["photo_file"] is None
    assert client.delete(f"{base}/cover-photo").json()["cover_photo"] is None
    assert client.get(f"{base}/{cover}").status_code == 404  # the file itself is gone


def test_making_the_story_again_keeps_pictures_by_page(client, settings):
    project_id = drafted_project(client, settings)["id"]
    base = f"/api/projects/{project_id}"
    client.put(f"{base}/pages/p1/photo", files={"file": ("a.png", image_bytes())})
    again = client.post(f"{base}/draft").json()
    assert again["chapters"][0]["photo_file"]


# --- clips and the book ------------------------------------------------------------------------------------

@needs_ffmpeg
def test_whole_flow_upload_story_clips_pdf_and_delete(client, settings):
    project_id = new_demo_project(client)
    upload = client.post(f"/api/projects/{project_id}/audio", files={"file": ("story.wav", sine_wav_bytes(6.0))})
    assert upload.status_code == 200 and upload.json()["audio_file"] == "audio/story.wav"
    give_fake_transcript(settings, project_id, count=4)
    client.post(f"/api/projects/{project_id}/draft")

    assert client.post(f"/api/projects/{project_id}/clips").json() == {"clips": ["p1.mp3", "p2.mp3"]}
    clip = client.get(f"/api/projects/{project_id}/clips/p1.mp3")
    assert clip.status_code == 200 and clip.headers["content-type"] == "audio/mpeg"
    ranged = client.get(f"/api/projects/{project_id}/clips/p1.mp3", headers={"Range": "bytes=0-99"})
    assert ranged.status_code == 206 and len(ranged.content) == 100  # phones need Range support to play audio

    printed = client.get(f"/api/projects/{project_id}/book.pdf?edition=print")
    assert printed.status_code == 200 and printed.content.startswith(b"%PDF")

    assert client.delete(f"/api/projects/{project_id}").status_code == 200
    assert client.get(f"/api/projects/{project_id}").status_code == 404
    assert not (settings.data_dir / "projects" / project_id).exists()


def test_both_book_editions_download(client, settings):
    project_id = reviewed_book(client, settings)
    family = client.get(f"/api/projects/{project_id}/book.pdf?edition=family")
    assert family.status_code == 200 and family.content.startswith(b"%PDF")
    assert "Gram-s-Day.pdf" in family.headers["content-disposition"]
    inline = client.get(f"/api/projects/{project_id}/book.pdf?edition=family&inline=true")
    assert inline.headers["content-disposition"].startswith("inline")
    printed = client.get(f"/api/projects/{project_id}/book.pdf?edition=print")
    assert printed.status_code == 200 and "-print.pdf" in printed.headers["content-disposition"]
    assert client.get(f"/api/projects/{project_id}/book.pdf?edition=poster").status_code == 422


def test_page_pictures_for_photo_book_services(client, settings):
    project_id = reviewed_book(client, settings)
    response = client.get(f"/api/projects/{project_id}/book-pages.zip")
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert names[0] == "README.txt" and names[1:] == ["page-01.jpg", "page-02.jpg", "page-03.jpg", "page-04.jpg", "page-05.jpg"]
    with Image.open(io.BytesIO(archive.read("page-01.jpg"))) as first:
        assert first.size == (2400, 2400)


# --- privacy on the network ----------------------------------------------------------------------------------

@needs_ffmpeg
def test_a_phone_on_the_network_can_play_clips_but_nothing_else(settings):
    local = TestClient(create_app(settings), client=LOCAL)
    phone = TestClient(create_app(settings), client=PHONE)
    project_id = new_demo_project(local)
    local.post(f"/api/projects/{project_id}/audio", files={"file": ("story.wav", sine_wav_bytes(6.0))})
    give_fake_transcript(settings, project_id, count=3)
    local.post(f"/api/projects/{project_id}/draft")
    local.post(f"/api/projects/{project_id}/clips")
    cover = local.put(f"/api/projects/{project_id}/cover-photo", files={"file": ("c.png", image_bytes())}).json()["cover_photo"]

    assert phone.get(f"/api/projects/{project_id}/clips/p1.mp3").status_code == 200
    for path in ("/api/projects", f"/api/projects/{project_id}", f"/api/projects/{project_id}/book.pdf",
                 f"/api/projects/{project_id}/audio", f"/api/projects/{project_id}/{cover}"):
        assert phone.get(path).status_code == 403, path
    assert phone.post(f"/api/projects/{project_id}/draft").status_code == 403
    assert phone.patch(f"/api/projects/{project_id}/sentences/p1-s1", json={"status": "approved"}).status_code == 403
    assert phone.delete(f"/api/projects/{project_id}").status_code == 403


@needs_ffmpeg
def test_recording_can_be_played_back_on_this_computer(client):
    project_id = new_demo_project(client)
    assert client.get(f"/api/projects/{project_id}/audio").status_code == 404  # no audio yet
    client.post(f"/api/projects/{project_id}/audio", files={"file": ("story.wav", sine_wav_bytes(2.0))})
    audio = client.get(f"/api/projects/{project_id}/audio")
    assert audio.status_code == 200 and audio.headers["content-type"] == "audio/wav"


def test_the_smilecard_website_is_served_next_to_the_app(client):
    home = client.get("/smilecard/")
    assert home.status_code == 200 and "SmileCard%20Home%20v7.dc.html" in home.text
    page = client.get("/smilecard/PageHero.dc.html")
    assert page.status_code == 200 and "label: 'StoryBridge', href: '../'" in page.text  # the site links to the app


def test_the_smilecard_website_is_only_for_this_computer(settings):
    phone = TestClient(create_app(settings), client=PHONE)
    assert phone.get("/smilecard/").status_code == 403
