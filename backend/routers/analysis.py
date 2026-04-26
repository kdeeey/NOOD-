"""
Analysis endpoints.

POST /api/analyze
    Upload a video file → returns job_id immediately.
    The pipeline runs in a background thread.

GET /api/analyze/{job_id}
    Poll for job status and (once done) the full report.
"""

from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Query

from backend.schemas.analysis import AnalyzeResponse, JobStatus, JobStatusResponse
from backend.services.job_manager import manager
from backend.services.pipeline import run_full_pipeline

router = APIRouter(prefix="/api/analyze", tags=["analysis"])

# Max upload size enforced at the app level (see main.py); keep this as a
# secondary guard in case the middleware is disabled.
_MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

_SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv",
}


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------

@router.post("", response_model=AnalyzeResponse, status_code=202)
async def submit_analysis(
    file: UploadFile = File(..., description="Presentation video file"),
    segment_duration: int = Query(
        default=30,
        ge=0,
        le=300,
        description="Speech segment window in seconds (0 = disable segmented analysis)",
    ),
) -> AnalyzeResponse:
    """Upload a video and start the analysis pipeline asynchronously."""

    # Basic extension check
    from pathlib import Path
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
            ),
        )

    # Read upload into memory (FastAPI streams to a SpooledTemporaryFile)
    video_bytes = await file.read()
    if len(video_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {_MAX_UPLOAD_BYTES // (1024**2)} MB.",
        )

    # Create job record
    job = manager.create()

    # Run pipeline in a thread so the event loop stays free
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        None,  # default ThreadPoolExecutor
        partial(
            _run_and_update,
            job.job_id,
            video_bytes,
            file.filename or "upload.mp4",
            segment_duration,
        ),
    )

    return AnalyzeResponse(job_id=job.job_id)


def _run_and_update(
    job_id: str,
    video_bytes: bytes,
    filename: str,
    segment_duration: int,
) -> None:
    """Blocking worker — executes in a thread, updates job state."""
    manager.mark_processing(job_id)
    try:
        report = run_full_pipeline(video_bytes, filename, segment_duration)
        manager.mark_done(job_id, report)
    except Exception as exc:  # noqa: BLE001
        manager.mark_failed(job_id, str(exc))


# ---------------------------------------------------------------------------
# GET /api/analyze/{job_id}
# ---------------------------------------------------------------------------

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    """Poll for job status. Once status is 'done', the full report is included."""
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return JobStatusResponse(
        job_id       = job.job_id,
        status       = job.status,
        created_at   = job.created_at,
        started_at   = job.started_at,
        completed_at = job.completed_at,
        error        = job.error,
        report       = job.report,  # None until done
    )
