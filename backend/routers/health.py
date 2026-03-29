from fastapi import APIRouter
from backend.schemas.analysis import HealthResponse
from backend.services.job_manager import manager

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(active_jobs=manager.active_count())
