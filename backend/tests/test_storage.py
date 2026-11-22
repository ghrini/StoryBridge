import pytest
from pydantic import ValidationError

from app.services.storage import ProjectNotFound, ProjectStore


def test_save_and_load_round_trip(tmp_path):
    store = ProjectStore(tmp_path)
    created = store.create(storyteller_name="Test", recording_kind="synthetic_dev")
    loaded = store.load(created.id)
    assert loaded == created


def test_list_ids_returns_saved_projects(tmp_path):
    store = ProjectStore(tmp_path)
    assert store.list_ids() == []
    first = store.create(recording_kind="synthetic_dev")
    second = store.create(recording_kind="synthetic_dev")
    assert store.list_ids() == sorted([first.id, second.id])


def test_save_leaves_no_temp_file(tmp_path):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="synthetic_dev")
    names = sorted(p.name for p in store.project_dir(project.id).iterdir())
    assert names == ["project.json"]


def test_delete_removes_everything_including_audio(tmp_path):
    store = ProjectStore(tmp_path)
    project = store.create(recording_kind="synthetic_dev")
    audio = store.project_dir(project.id) / "audio"
    audio.mkdir()
    (audio / "story.wav").write_bytes(b"fake audio")
    store.delete(project.id)
    assert not store.project_dir(project.id).exists()
    with pytest.raises(ProjectNotFound):
        store.load(project.id)


@pytest.mark.parametrize("bad_id", ["../etc", "..", "ABCD1234", "abc", "abcd1234/../x", "", "abcd123g"])
def test_bad_project_ids_are_rejected(tmp_path, bad_id):
    store = ProjectStore(tmp_path)
    with pytest.raises(ProjectNotFound):
        store.project_dir(bad_id)
    with pytest.raises(ProjectNotFound):
        store.load(bad_id)


def test_loading_a_missing_project_raises(tmp_path):
    with pytest.raises(ProjectNotFound):
        ProjectStore(tmp_path).load("abcd1234")


def test_creating_a_storyteller_project_without_consent_fails(tmp_path):
    with pytest.raises(ValidationError):
        ProjectStore(tmp_path).create(recording_kind="storyteller")
