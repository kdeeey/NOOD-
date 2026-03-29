"""
In-memory job store.

Each job transitions:  QUEUED → PROCESSING → DONE | FAILED

Thread-safe for use with FastAPI's default threadpool executor
(asyncio.loop.run_in_executor runs the pipeline in a thread).
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.schemas.analysis import JobStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job:
    __slots__ = (
        "job_id", "status", "created_at", "started_at",
        "completed_at", "error", "report",
    )

    def __init__(self, job_id: str):
        self.job_id      : str                  = job_id
        self.status      : JobStatus            = JobStatus.QUEUED
        self.created_at  : datetime             = _utcnow()
        self.started_at  : Optional[datetime]   = None
        self.completed_at: Optional[datetime]   = None
        self.error       : Optional[str]        = None
        self.report      : Optional[Dict[str, Any]] = None


class JobManager:
    """Thread-safe store for analysis jobs."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def create(self) -> Job:
        job = Job(job_id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def mark_processing(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status     = JobStatus.PROCESSING
        job.started_at = _utcnow()

    def mark_done(self, job_id: str, report: Dict[str, Any]) -> None:
        job = self._jobs[job_id]
        job.status       = JobStatus.DONE
        job.completed_at = _utcnow()
        job.report       = report

    def mark_failed(self, job_id: str, error: str) -> None:
        job = self._jobs[job_id]
        job.status       = JobStatus.FAILED
        job.completed_at = _utcnow()
        job.error        = error

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def active_count(self) -> int:
        return sum(
            1 for j in self._jobs.values()
            if j.status in (JobStatus.QUEUED, JobStatus.PROCESSING)
        )


# Singleton used by the FastAPI app
manager = JobManager()
