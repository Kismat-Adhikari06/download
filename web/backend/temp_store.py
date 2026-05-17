"""
temp_store.py — in-memory registry of active download jobs.

Thread-safe via threading.Lock (APScheduler runs in a background thread).
"""

import threading
from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobRecord:
    """Metadata for a single download job."""

    job_id: str
    file_path: str    # absolute path to the downloaded file on disk
    filename: str     # basename used in Content-Disposition header
    created_at: datetime  # UTC timestamp, used for expiry checks


class TempStore:
    """In-memory store for active download jobs.

    All public methods are protected by a threading.Lock so they are safe
    to call from both the FastAPI request handlers and the APScheduler
    background thread.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, JobRecord] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, record: JobRecord) -> None:
        """Add *record* to the store, keyed by ``record.job_id``."""
        with self._lock:
            self._records[record.job_id] = record

    def get(self, job_id: str) -> JobRecord | None:
        """Return the record for *job_id*, or ``None`` if not found."""
        with self._lock:
            return self._records.get(job_id)

    def remove(self, job_id: str) -> None:
        """Remove the record for *job_id* (no-op if not present)."""
        with self._lock:
            self._records.pop(job_id, None)

    # ------------------------------------------------------------------
    # Expiry
    # ------------------------------------------------------------------

    def expired_jobs(self, max_age_seconds: int = 3600) -> list[JobRecord]:
        """Return all records whose age exceeds *max_age_seconds*.

        Age is computed as ``(datetime.utcnow() - record.created_at).total_seconds()``.
        The default threshold is 3600 seconds (1 hour).
        """
        now = datetime.utcnow()
        with self._lock:
            return [
                record
                for record in self._records.values()
                if (now - record.created_at).total_seconds() > max_age_seconds
            ]
