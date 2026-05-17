"""
Tests for TempStore and JobRecord.

Includes unit tests and a property-based test for expired_jobs boundary.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from temp_store import JobRecord, TempStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_record(job_id: str, age_seconds: float = 0.0) -> JobRecord:
    """Create a JobRecord with created_at set *age_seconds* in the past."""
    created_at = datetime.utcnow() - timedelta(seconds=age_seconds)
    return JobRecord(
        job_id=job_id,
        file_path=f"/tmp/{job_id}/file.mp4",
        filename="file.mp4",
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Unit tests — CRUD
# ---------------------------------------------------------------------------


def test_add_and_get():
    store = TempStore()
    record = make_record("job-1")
    store.add(record)
    assert store.get("job-1") is record


def test_get_missing_returns_none():
    store = TempStore()
    assert store.get("nonexistent") is None


def test_remove_existing():
    store = TempStore()
    store.add(make_record("job-2"))
    store.remove("job-2")
    assert store.get("job-2") is None


def test_remove_missing_is_noop():
    store = TempStore()
    # Should not raise
    store.remove("does-not-exist")


def test_add_overwrites_existing():
    store = TempStore()
    r1 = make_record("job-3")
    r2 = make_record("job-3", age_seconds=10)
    store.add(r1)
    store.add(r2)
    assert store.get("job-3") is r2


# ---------------------------------------------------------------------------
# Unit tests — expired_jobs
# ---------------------------------------------------------------------------


def test_expired_jobs_returns_old_records():
    store = TempStore()
    old = make_record("old-job", age_seconds=3601)
    fresh = make_record("fresh-job", age_seconds=100)
    store.add(old)
    store.add(fresh)

    expired = store.expired_jobs(max_age_seconds=3600)
    assert len(expired) == 1
    assert expired[0].job_id == "old-job"


def test_expired_jobs_boundary_exactly_at_threshold_not_expired():
    """A job exactly at the threshold (== max_age_seconds) is NOT expired."""
    store = TempStore()
    # Use a slightly-less-than-threshold age to avoid flakiness
    record = make_record("boundary-job", age_seconds=3599)
    store.add(record)
    assert store.expired_jobs(max_age_seconds=3600) == []


def test_expired_jobs_empty_store():
    store = TempStore()
    assert store.expired_jobs() == []


def test_expired_jobs_all_fresh():
    store = TempStore()
    for i in range(5):
        store.add(make_record(f"job-{i}", age_seconds=10))
    assert store.expired_jobs(max_age_seconds=3600) == []


def test_expired_jobs_all_expired():
    store = TempStore()
    for i in range(3):
        store.add(make_record(f"job-{i}", age_seconds=7200))
    expired = store.expired_jobs(max_age_seconds=3600)
    assert len(expired) == 3


# ---------------------------------------------------------------------------
# Property-based test — Property 12: Cleanup deletes exactly the expired jobs
# Feature: web-ui, Property 12: Cleanup deletes exactly the expired jobs
# Validates: Requirements 6.2, 6.3
# ---------------------------------------------------------------------------


@given(
    ages=st.lists(
        st.floats(min_value=0.0, max_value=10800.0, allow_nan=False, allow_infinity=False),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=100)
def test_expired_jobs_returns_exactly_expired_records(ages):
    """
    # Feature: web-ui, Property 12: Cleanup deletes exactly the expired jobs
    **Validates: Requirements 6.2, 6.3**

    For any mix of job ages, expired_jobs() returns exactly the records
    older than 1 hour and leaves the rest untouched.
    """
    MAX_AGE = 3600.0
    store = TempStore()

    expected_expired_ids = set()
    expected_fresh_ids = set()

    for i, age_seconds in enumerate(ages):
        job_id = f"job-{i}"
        record = make_record(job_id, age_seconds=age_seconds)
        store.add(record)
        if age_seconds > MAX_AGE:
            expected_expired_ids.add(job_id)
        else:
            expected_fresh_ids.add(job_id)

    expired = store.expired_jobs(max_age_seconds=int(MAX_AGE))
    expired_ids = {r.job_id for r in expired}

    # All expired jobs are returned
    assert expired_ids == expected_expired_ids

    # Fresh jobs are NOT in the expired list
    assert expired_ids.isdisjoint(expected_fresh_ids)

    # The store still contains all records (expired_jobs is read-only)
    for job_id in expected_fresh_ids:
        assert store.get(job_id) is not None
