"""
scheduler.py — APScheduler wrapper for periodic temp-file cleanup.
"""

import shutil
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from temp_store import TempStore


def cleanup_expired_jobs(store: TempStore) -> None:
    """Delete files and records for all expired jobs.

    For each expired ``JobRecord``:
    1. Removes the job's parent directory (and all its contents) from disk.
    2. Removes the record from *store* in a ``finally`` block so the store
       stays consistent even if the filesystem operation fails.
    """
    for record in store.expired_jobs():
        try:
            parent_dir = Path(record.file_path).parent
            shutil.rmtree(parent_dir, ignore_errors=True)
        finally:
            store.remove(record.job_id)


def start_scheduler(store: TempStore) -> BackgroundScheduler:
    """Create, configure, and start a background scheduler.

    Runs :func:`cleanup_expired_jobs` every 5 minutes.

    Returns
    -------
    BackgroundScheduler
        The running scheduler instance (caller should keep a reference and
        call :func:`stop_scheduler` on shutdown).
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        cleanup_expired_jobs,
        trigger="interval",
        minutes=5,
        args=[store],
        id="cleanup_expired_jobs",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    """Shut down *scheduler* gracefully, waiting for running jobs to finish."""
    scheduler.shutdown(wait=True)
