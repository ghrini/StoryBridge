"""Project storage: one folder per project under data/projects/<id>/ holding project.json,
the audio, clips, and illustrations. No database. Deleting a project deletes its folder,
which is how a storyteller's withdrawal removes their recording."""
import os
import re
import shutil
import uuid
from pathlib import Path

from ..schemas import ConsentRecord, RecordingKind, StoryProject

PROJECT_ID_RE = re.compile(r"^[0-9a-f]{8}$")


class ProjectNotFound(Exception):
    pass


class ProjectStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "projects"

    def project_dir(self, project_id: str) -> Path:
        # IDs arrive from URLs, so reject anything that is not exactly what create() makes.
        if not PROJECT_ID_RE.fullmatch(project_id):
            raise ProjectNotFound(project_id)
        return self.root / project_id

    def create(
        self,
        storyteller_name: str | None = None,
        recording_kind: RecordingKind = "storyteller",
        consent: ConsentRecord | None = None,
    ) -> StoryProject:
        project = StoryProject(
            id=uuid.uuid4().hex[:8],
            storyteller_name=storyteller_name,
            recording_kind=recording_kind,
            consent=consent,
        )
        self.save(project)
        return project

    def save(self, project: StoryProject) -> None:
        folder = self.project_dir(project.id)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "project.json"
        temp = folder / "project.json.tmp"
        temp.write_text(project.model_dump_json(indent=2), encoding="utf-8")
        os.replace(temp, target)  # a crash mid-write never leaves a half-written project.json

    def load(self, project_id: str) -> StoryProject:
        path = self.project_dir(project_id) / "project.json"
        if not path.is_file():
            raise ProjectNotFound(project_id)
        return StoryProject.model_validate_json(path.read_text(encoding="utf-8"))

    def list_ids(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(p.name for p in self.root.iterdir() if (p / "project.json").is_file())

    def delete(self, project_id: str) -> None:
        """Remove the whole project folder: recordings, transcript, clips, everything."""
        folder = self.project_dir(project_id)
        if not folder.is_dir():
            raise ProjectNotFound(project_id)
        shutil.rmtree(folder)
