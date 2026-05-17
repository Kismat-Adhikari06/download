"""
Tests for FastAPI routes in main.py.

Includes unit tests and property-based tests for:
  - Property 8:  Invalid format values always return 422
  - Property 9:  File serving always sets Content-Disposition: attachment
  - Property 10: Missing job IDs always return 404
  - Property 11: Served files are always deleted after retrieval
"""

import os
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main as app_module
from temp_store import JobRecord, TempStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def _test_client(store: TempStore, tmp_dir: str):
    """Context manager that yields a TestClient with injected store/temp_root.

    The lifespan runs on entry and resets _store/_temp_root, so we inject
    our test values immediately after startup completes.
    """
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        # Inject test state AFTER lifespan startup has run
        app_module._store = store
        app_module._temp_root = tmp_dir
        app_module._scheduler = None
        yield client


def _add_job(store: TempStore, tmp_dir: str, content: bytes = b"fake") -> tuple[str, Path]:
    """Write a file to tmp_dir and register it in store. Returns (job_id, file_path)."""
    job_id = str(uuid.uuid4())
    job_dir = Path(tmp_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    file_path = job_dir / "media.mp4"
    file_path.write_bytes(content)

    record = JobRecord(
        job_id=job_id,
        file_path=str(file_path),
        filename="media.mp4",
        created_at=datetime.utcnow(),
    )
    store.add(record)
    return job_id, file_path


# ---------------------------------------------------------------------------
# Unit tests — POST /download
# ---------------------------------------------------------------------------


def test_post_download_success(tmp_path):
    store = TempStore()
    fake_file = tmp_path / "fake_job" / "video.mp4"
    fake_file.parent.mkdir(parents=True, exist_ok=True)
    fake_file.write_bytes(b"fake video")

    with _test_client(store, str(tmp_path)) as client:
        with patch("main.download_to_path", return_value=str(fake_file)):
            resp = client.post(
                "/download", json={"url": "https://example.com/v", "format": "video"}
            )

    assert resp.status_code == 200
    data = resp.json()
    assert "download_url" in data
    assert "filename" in data
    assert data["filename"] == "video.mp4"
    assert "video.mp4" in data["download_url"]


def test_post_download_empty_url_returns_422(tmp_path):
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        resp = client.post("/download", json={"url": "", "format": "video"})
    assert resp.status_code == 422


def test_post_download_missing_url_returns_422(tmp_path):
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        resp = client.post("/download", json={"format": "video"})
    assert resp.status_code == 422


def test_post_download_invalid_format_returns_422(tmp_path):
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        resp = client.post(
            "/download", json={"url": "https://example.com", "format": "gif"}
        )
    assert resp.status_code == 422


def test_post_download_download_error_returns_500(tmp_path):
    import yt_dlp.utils

    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        with patch(
            "main.download_to_path",
            side_effect=yt_dlp.utils.DownloadError("network error"),
        ):
            resp = client.post(
                "/download", json={"url": "https://example.com", "format": "video"}
            )

    assert resp.status_code == 500
    assert "network error" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Unit tests — GET /files/{job_id}/{filename}
# ---------------------------------------------------------------------------


def test_get_file_success(tmp_path):
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        job_id, _ = _add_job(store, str(tmp_path), content=b"hello world")
        resp = client.get(f"/files/{job_id}/media.mp4")

    assert resp.status_code == 200
    assert resp.content == b"hello world"


def test_get_file_sets_content_disposition_attachment(tmp_path):
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        job_id, _ = _add_job(store, str(tmp_path))
        resp = client.get(f"/files/{job_id}/media.mp4")

    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd


def test_get_file_missing_job_returns_404(tmp_path):
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        resp = client.get(f"/files/{uuid.uuid4()}/media.mp4")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "File not found"


def test_get_file_removes_job_from_store(tmp_path):
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        job_id, _ = _add_job(store, str(tmp_path))
        client.get(f"/files/{job_id}/media.mp4")

    # Background task runs synchronously in TestClient
    assert store.get(job_id) is None


# ---------------------------------------------------------------------------
# Property 8: Invalid format values always return 422
# Feature: web-ui, Property 8: Invalid format values always return 422
# Validates: Requirements 4.5
# ---------------------------------------------------------------------------


@given(fmt=st.text().filter(lambda s: s not in ("video", "audio")))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_invalid_format_always_returns_422(fmt, tmp_path):
    """
    # Feature: web-ui, Property 8: Invalid format values always return 422
    **Validates: Requirements 4.5**
    """
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        resp = client.post(
            "/download", json={"url": "https://example.com", "format": fmt}
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Property 9: File serving always sets Content-Disposition: attachment
# Feature: web-ui, Property 9: File serving always sets Content-Disposition: attachment
# Validates: Requirements 5.2
# ---------------------------------------------------------------------------


@given(content=st.binary(min_size=1, max_size=1024))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_file_serving_always_sets_attachment_header(content, tmp_path):
    """
    # Feature: web-ui, Property 9: File serving always sets Content-Disposition: attachment
    **Validates: Requirements 5.2**
    """
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        job_id, _ = _add_job(store, str(tmp_path), content=content)
        resp = client.get(f"/files/{job_id}/media.mp4")

    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd


# ---------------------------------------------------------------------------
# Property 10: Missing job IDs always return 404
# Feature: web-ui, Property 10: Missing job IDs always return 404
# Validates: Requirements 5.3
# ---------------------------------------------------------------------------


@given(job_id=st.uuids())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_missing_job_id_always_returns_404(job_id, tmp_path):
    """
    # Feature: web-ui, Property 10: Missing job IDs always return 404
    **Validates: Requirements 5.3**
    """
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        resp = client.get(f"/files/{job_id}/media.mp4")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Property 11: Served files are always deleted after retrieval
# Feature: web-ui, Property 11: Served files are always deleted after retrieval
# Validates: Requirements 5.4
# ---------------------------------------------------------------------------


@given(content=st.binary(min_size=1, max_size=1024))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_served_files_deleted_after_retrieval(content, tmp_path):
    """
    # Feature: web-ui, Property 11: Served files are always deleted after retrieval
    **Validates: Requirements 5.4**
    """
    store = TempStore()
    with _test_client(store, str(tmp_path)) as client:
        job_id, file_path = _add_job(store, str(tmp_path), content=content)
        resp = client.get(f"/files/{job_id}/media.mp4")

    assert resp.status_code == 200
    # File should be deleted (background task runs synchronously in TestClient)
    assert not file_path.exists()
    # Job record should be removed
    assert store.get(job_id) is None
