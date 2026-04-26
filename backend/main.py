"""
NOOD Presentation Analyzer — FastAPI backend.

Start with:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Or from the NOOD project root:
    python -m uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import analysis, health

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NOOD Presentation Analyzer API",
    description=(
        "Upload a presentation video and get a detailed performance report "
        "covering body language, speech prosody, and tone-content fit."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — adjust origins for production
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(analysis.router)
