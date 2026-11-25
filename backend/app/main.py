"""StoryBridge API.

Run from the repo root:
    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000

Privacy: everything except the audio-clip links answers only to requests from this computer, so a
phone on the same Wi-Fi can play a page's voice clip (that is what the QR codes link to) but cannot
list projects, read transcripts, see pictures, or download books.
"""
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .config import REPO_ROOT, REVIEW_NOTICE, Settings, load_settings
from .schemas import ConsentRecord, Pronouns, RecordingKind, SentenceStatus, StoryProject
from .services.book_export import page_images_zip
from .services.book_pdf import ExportBlocked, book_title_for, build_pdf, check_ready, file_slug
from .services.book_preview import build_preview, preview_page_path
from .services.clips import build_clips
from .services.drafting import (
    DraftError, HelperUnavailable, SentenceNotFound, ai_helper_status, confirm_story, draft_story, revise_story,
    update_sentence,
)
from .services.photos import PhotoError, PhotoNotFound, photo_path, save_photo, set_chapter_photo, set_cover_photo
from .services.record import AudioError, ConsentError, add_audio
from .services.storage import ProjectNotFound, ProjectStore
from .services.transcribe import transcribe_project

LOCAL_CLIENTS = {"127.0.0.1", "::1"}
# Added by web hosts and tunnels (Vercel, Cloudflare, Tailscale Serve, ...). They pass requests on from
# 127.0.0.1, so a request carrying one of these never counts as coming from this computer.
PROXY_HEADERS = ("forwarded", "x-forwarded-for", "x-real-ip", "x-vercel-id", "cf-connecting-ip")
PAGE_ID = r"(?:p|ch)\d+"  # "p3" = page 3 ("ch" ids are from books made before pages)
CLIP_PATH = re.compile(rf"^/api/projects/[0-9a-f]{{8}}/clips/{PAGE_ID}\.mp3$")


class NewProject(BaseModel):
    storyteller_name: str | None = None
    recording_kind: RecordingKind = "storyteller"
    consent: ConsentRecord | None = None


class BookDetails(BaseModel):
    family_name: str | None = None
    pronouns: Pronouns | None = None
    book_title: str | None = None


class SentenceUpdate(BaseModel):
    status: SentenceStatus | None = None
    text: str | None = None


class ChangeRequest(BaseModel):
    request: str  # what the reviewer would like changed, in their own words


def _clean(value):
    return (value.strip() or None) if isinstance(value, str) else value


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = ProjectStore(settings.data_dir)
    app = FastAPI(title="StoryBridge")

    @app.middleware("http")
    async def keep_private_data_on_this_computer(request: Request, call_next):
        client = request.client.host if request.client else ""
        local = client in LOCAL_CLIENTS and not any(name in request.headers for name in PROXY_HEADERS)
        if not local and not CLIP_PATH.match(request.url.path):
            return JSONResponse({"detail": "This is only available on the computer running StoryBridge."},
                                status_code=403)
        return await call_next(request)

    def error_response(status: int):
        async def handler(_request: Request, error: Exception):
            if isinstance(error, ProjectNotFound):
                message = "Project not found."
            elif isinstance(error, PhotoNotFound):
                message = "Not found."
            else:
                message = str(error)
            return JSONResponse({"detail": message}, status_code=status)
        return handler

    app.add_exception_handler(ProjectNotFound, error_response(404))
    app.add_exception_handler(ConsentError, error_response(403))
    app.add_exception_handler(AudioError, error_response(400))
    app.add_exception_handler(ExportBlocked, error_response(409))
    app.add_exception_handler(DraftError, error_response(422))
    app.add_exception_handler(HelperUnavailable, error_response(409))
    app.add_exception_handler(SentenceNotFound, error_response(404))
    app.add_exception_handler(PhotoError, error_response(400))
    app.add_exception_handler(PhotoNotFound, error_response(404))

    def find_page(project: StoryProject, page_id: str):
        page = next((c for c in project.chapters if c.id == page_id), None)
        if page is None:
            raise HTTPException(404, "Page not found.")
        return page

    # --- basics ------------------------------------------------------------------------------

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/config")
    def get_config():
        return {
            "base_url": settings.base_url,
            "review_notice": REVIEW_NOTICE,
            "whisper_model": settings.whisper_model,
            "ai_model": settings.gemini_model if settings.gemini_api_key else None,
        }

    @app.post("/api/projects")
    def create_project(request: NewProject) -> StoryProject:
        try:
            return store.create(request.storyteller_name, request.recording_kind, request.consent)
        except ValidationError as error:
            raise HTTPException(422, error.errors()[0]["msg"]) from error

    @app.get("/api/projects")
    def list_projects():
        summaries = []
        for project_id in store.list_ids():
            project = store.load(project_id)
            summaries.append({
                "id": project.id,
                "storyteller_name": project.storyteller_name,
                "family_name": project.family_name,
                "book_title": book_title_for(project) if project.chapters else None,
                "recording_kind": project.recording_kind,
                "duration_seconds": project.duration_seconds,
                "pages": len(project.chapters),
            })
        return summaries

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> StoryProject:
        return store.load(project_id)

    @app.patch("/api/projects/{project_id}")
    def update_book_details(project_id: str, request: BookDetails) -> StoryProject:
        """What the family calls the storyteller, their pronouns, and the book's title."""
        project = store.load(project_id)
        for field in request.model_fields_set:
            setattr(project, field, _clean(getattr(request, field)))
        store.save(project)
        return project

    @app.delete("/api/projects/{project_id}")
    def delete_project(project_id: str):
        """Withdrawal: removes the recording, transcript, clips, pictures, and everything else."""
        store.delete(project_id)
        return {"deleted": project_id}

    # --- recording, text, and the story --------------------------------------------------------

    @app.post("/api/projects/{project_id}/audio")
    def upload_audio(project_id: str, file: UploadFile = File(...)) -> StoryProject:
        project = store.load(project_id)
        return add_audio(store, project, file.filename or "", file.file, settings)

    @app.get("/api/projects/{project_id}/audio")
    def get_audio(project_id: str):
        """The prepared recording, so a person can listen while checking the story."""
        project = store.load(project_id)
        if not project.audio_file:
            raise HTTPException(404, "No audio yet.")
        return FileResponse(store.project_dir(project.id) / project.audio_file, media_type="audio/wav")

    @app.post("/api/projects/{project_id}/transcribe")
    def transcribe(project_id: str) -> StoryProject:
        project = store.load(project_id)
        if not project.recording_allowed():
            raise ConsentError("This project has no consent to record, or consent was withdrawn.")
        if not project.audio_file:
            raise HTTPException(409, "Upload audio first.")
        return transcribe_project(store, project, settings)

    @app.post("/api/projects/{project_id}/draft")
    def draft(project_id: str, replay: bool = False) -> StoryProject:
        """Make the storybook pages from the transcript. AI-written sentences start as 'needs review'.
        With ?replay=true, only a saved draft or the storyteller's own words are used (nothing is sent anywhere)."""
        return draft_story(store, store.load(project_id), settings, replay=replay)

    @app.get("/api/projects/{project_id}/ai-helper")
    def get_ai_helper(project_id: str):
        """Whether "ask for changes" can be used for this story, and if not, why."""
        return ai_helper_status(store.load(project_id), settings)

    @app.post("/api/projects/{project_id}/revise")
    def revise(project_id: str, body: ChangeRequest):
        """Change the story the way the reviewer asks. Only transcript and book text are sent, never audio.
        New or changed sentences need reading again before the book can be shared."""
        project, reply, changed = revise_story(store, store.load(project_id), settings, body.request)
        return {"project": project, "reply": reply, "changed_pages": changed}

    @app.post("/api/projects/{project_id}/confirm")
    def confirm(project_id: str) -> StoryProject:
        """A person read the whole story with the storyteller or family and says it is right."""
        project = store.load(project_id)
        confirm_story(project)
        store.save(project)
        return project

    @app.patch("/api/projects/{project_id}/sentences/{sentence_id}")
    def review_sentence(project_id: str, sentence_id: str, request: SentenceUpdate) -> StoryProject:
        """A change to one sentence by hand: remove it, put it back, or rewrite it."""
        project = store.load(project_id)
        update_sentence(project, sentence_id, request.status, request.text)
        store.save(project)
        return project

    # --- pictures ----------------------------------------------------------------------------

    @app.put("/api/projects/{project_id}/cover-photo")
    def put_cover_photo(project_id: str, file: UploadFile = File(...)) -> StoryProject:
        project = store.load(project_id)
        set_cover_photo(store, project, save_photo(store, project, file.filename or "", file.file))
        store.save(project)
        return project

    @app.delete("/api/projects/{project_id}/cover-photo")
    def delete_cover_photo(project_id: str) -> StoryProject:
        project = store.load(project_id)
        set_cover_photo(store, project, None)
        store.save(project)
        return project

    @app.put("/api/projects/{project_id}/pages/{page_id}/photo")
    def put_page_photo(project_id: str, page_id: str, file: UploadFile = File(...)) -> StoryProject:
        project = store.load(project_id)
        find_page(project, page_id)
        set_chapter_photo(store, project, page_id, save_photo(store, project, file.filename or "", file.file))
        store.save(project)
        return project

    @app.delete("/api/projects/{project_id}/pages/{page_id}/photo")
    def delete_page_photo(project_id: str, page_id: str) -> StoryProject:
        project = store.load(project_id)
        find_page(project, page_id)
        set_chapter_photo(store, project, page_id, None)
        store.save(project)
        return project

    @app.get("/api/projects/{project_id}/photos/{name}")
    def get_photo(project_id: str, name: str):
        store.load(project_id)
        return FileResponse(photo_path(store, project_id, name), media_type="image/jpeg")

    # --- voice clips and the book ---------------------------------------------------------------

    @app.post("/api/projects/{project_id}/clips")
    def make_clips(project_id: str):
        project = store.load(project_id)
        try:
            return {"clips": build_clips(store, project, settings)}
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/api/projects/{project_id}/clips/{page_id}.mp3")
    def get_clip(project_id: str, page_id: str):
        clip = store.project_dir(project_id) / "clips" / f"{page_id}.mp3"
        if not re.fullmatch(PAGE_ID, page_id) or not clip.is_file():
            raise HTTPException(404, "Clip not found.")
        return FileResponse(clip, media_type="audio/mpeg")

    def built_book(project: StoryProject, edition: str) -> Path:
        try:
            check_ready(project)
            if edition == "print" and project.audio_file:
                build_clips(store, project, settings)  # the QR codes point at these clips
            return build_pdf(project, store.project_dir(project.id), settings, edition)
        except ExportBlocked:
            raise
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

    @app.get("/api/projects/{project_id}/book.pdf")
    def get_book(project_id: str, edition: Literal["print", "family"] = "print", inline: bool = False):
        """print: with bleed and voice QR codes, for print services. family: for sending to family."""
        project = store.load(project_id)
        path = built_book(project, edition)
        name = file_slug(book_title_for(project)) + ("-print" if edition == "print" else "") + ".pdf"
        return FileResponse(path, media_type="application/pdf", filename=name,
                            content_disposition_type="inline" if inline else "attachment")

    @app.get("/api/projects/{project_id}/book-preview")
    def get_book_preview(project_id: str):
        """Pictures of every page for the in-app page flipper. Works before the story is confirmed, but then
        every page is stamped PREVIEW; downloads and sharing need a person to confirm the story first."""
        project = store.load(project_id)
        try:
            result = build_preview(project, store.project_dir(project.id), settings)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return {
            "title": book_title_for(project),
            "reviewed": result["reviewed"],
            "pages": [f"/api/projects/{project.id}/preview/{name}" for name in result["pages"]],
        }

    @app.get("/api/projects/{project_id}/preview/{name}")
    def get_preview_page(project_id: str, name: str):
        store.load(project_id)
        path = preview_page_path(store.project_dir(project_id), name)
        if path is None:
            raise HTTPException(404, "Preview page not found.")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/api/projects/{project_id}/book-pages.zip")
    def get_book_pages(project_id: str):
        """One 2400 x 2400 pixel picture per page, for photo-book services that build books from photos."""
        project = store.load(project_id)
        data = page_images_zip(built_book(project, "family"))
        name = file_slug(book_title_for(project)) + "-pages.zip"
        return Response(data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}"'})

    # The student's redesigned SmileCard website, whose menu links to StoryBridge (and back).
    site = Path(REPO_ROOT / "smilecard-site")
    if site.is_dir():
        app.mount("/smilecard", StaticFiles(directory=site, html=True), name="smilecard")

    frontend = Path(REPO_ROOT / "frontend" / "dist")
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")

    return app


app = create_app()
