"""
Pydantic request/response schemas for the analysis API.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Job lifecycle
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    QUEUED     = "queued"
    PROCESSING = "processing"
    DONE       = "done"
    FAILED     = "failed"


# ---------------------------------------------------------------------------
# POST /api/analyze  (response)
# ---------------------------------------------------------------------------

class AnalyzeResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = "Analysis queued. Poll /api/analyze/{job_id} for results."


# ---------------------------------------------------------------------------
# GET /api/analyze/{job_id}  (response)
# ---------------------------------------------------------------------------

class ComponentScores(BaseModel):
    speech_score: float
    body_language_score: float
    tone_fit_score: float


class BodyLanguageSummary(BaseModel):
    total_frames_analyzed: int
    dominant_emotion: str
    dominant_emotion_pct: float
    average_confidence: float
    emotion_distribution: Dict[str, float]
    duration_s: float


class BodyLanguageReport(BaseModel):
    summary: BodyLanguageSummary
    # per-frame data omitted from response by default (can be large)


class Marker(BaseModel):
    score: float
    raw: float
    unit: str
    label: str
    feedback: str


class SpeechReport(BaseModel):
    overall: float
    grade: str
    wpm: Marker
    filler_rate: Marker
    pitch_variation: Marker
    energy_variation: Marker
    pause_ratio: Marker
    vocal_emotion: Marker
    transcript_preview: str
    segments: List[Dict[str, Any]] = Field(default_factory=list)


class ToneMismatch(BaseModel):
    severity: str
    observed_tone: str
    expected_tone: str
    reason: str
    moment: str


class ToneReport(BaseModel):
    detected_topic: str
    detected_context: str
    overall_tone_fit: str
    tone_fit_score: float
    mismatches: List[ToneMismatch] = Field(default_factory=list)
    coaching_tips: List[str] = Field(default_factory=list)
    model_used: str


class ReportMeta(BaseModel):
    video: str
    generated_at: str
    pipeline_duration_s: float
    segment_duration: int


class TimelineEvent(BaseModel):
    timestamp_s: float
    source: str
    event: str
    confidence: Optional[float] = None
    pitch_score: Optional[float] = None
    energy_score: Optional[float] = None


class AnalysisReport(BaseModel):
    meta: ReportMeta
    overall_score: float
    overall_grade: str
    component_scores: ComponentScores
    body_language_score: float
    body_language: Dict[str, Any]   # full body_language dict (summary + frames)
    speech: Dict[str, Any]          # full SpeechReport dict
    tone: Dict[str, Any]            # full ToneReport dict (raw_response stripped)
    timeline: List[Dict[str, Any]]


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    report: Optional[AnalysisReport] = None


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    active_jobs: int
