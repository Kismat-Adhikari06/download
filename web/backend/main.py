"""
main.py — FastAPI application for the Universal Media Downloader web UI.
"""

import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import yt_dlp.utils

from downloader_core import download_to_path
from scheduler import start_scheduler, stop_scheduler
from temp_store import JobRecord, TempStore

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class DownloadRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Media URL to download")
    format: Literal["video", "audio"] = Field(
        "video", description="Output format: 'video' (MP4) or 'audio' (MP3)"
    )


class DownloadResponse(BaseModel):
    download_url: str
    filename: str


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Application state (populated during lifespan)
# ---------------------------------------------------------------------------

_store: TempStore | None = None
_scheduler = None
_temp_root: str | None = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _store, _scheduler, _temp_root

    # Startup
    _temp_root = os.environ.get("TEMP_DIR") or tempfile.mkdtemp(
        prefix="media_downloader_"
    )
    os.makedirs(_temp_root, exist_ok=True)

    _store = TempStore()
    _scheduler = start_scheduler(_store)

    yield

    # Shutdown
    if _scheduler is not None:
        stop_scheduler(_scheduler)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="Universal Media Downloader",
        description="Web API for downloading media via yt-dlp",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow origins from env var; use "*" if set to wildcard for Railway
    allowed_origins_raw = os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:5173"
    )
    if allowed_origins_raw.strip() == "*":
        allowed_origins = ["*"]
    else:
        allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handler for yt-dlp download errors
    @app.exception_handler(yt_dlp.utils.DownloadError)
    async def download_error_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/health")
    async def health_check():
        """Railway health check endpoint."""
        return {"status": "healthy"}



    @app.post("/download", response_model=DownloadResponse, status_code=200)
    async def post_download(body: DownloadRequest):
        """Accept a URL + format, run yt-dlp, return a temporary download link."""
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(_temp_root, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # This may raise yt_dlp.utils.DownloadError (handled above) or ValueError
        try:
            file_path = download_to_path(body.url, body.format, job_dir)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        filename = Path(file_path).name

        record = JobRecord(
            job_id=job_id,
            file_path=file_path,
            filename=filename,
            created_at=__import__("datetime").datetime.utcnow(),
        )
        _store.add(record)

        return DownloadResponse(
            download_url=f"/files/{job_id}/{filename}",
            filename=filename,
        )

    @app.get("/files/{job_id}/{filename}")
    async def get_file(
        job_id: str, filename: str, background_tasks: BackgroundTasks
    ):
        """Serve the file for *job_id* as an attachment, then delete it."""
        record = _store.get(job_id)
        if record is None:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = record.file_path
        if not Path(file_path).exists():
            _store.remove(job_id)
            raise HTTPException(status_code=404, detail="File not found")

        def _cleanup():
            try:
                import shutil
                parent = Path(file_path).parent
                shutil.rmtree(parent, ignore_errors=True)
            finally:
                _store.remove(job_id)

        background_tasks.add_task(_cleanup)

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            },
        )

    return app


app = create_app()
