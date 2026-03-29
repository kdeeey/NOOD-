"""
Thin wrapper around the existing analysis pipeline.

Runs  presentation_analyzer.run_pipeline()  in a background thread
(called via asyncio.loop.run_in_executor so it doesn't block the event loop).

sys.path is patched here once so every import inside run_pipeline works
regardless of where uvicorn is launched from.
"""

from __future__ import annotations

import sys
import tempfile
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — must happen before any project-level import
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]   # …/NOOD
_BODY_DIR     = _PROJECT_ROOT / "Body Analysis"
_SPEECH_DIR   = _PROJECT_ROOT / "Speech Analysis"

for _p in (_PROJECT_ROOT, _BODY_DIR, _SPEECH_DIR):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
# ---------------------------------------------------------------------------

from typing import Any, Dict


def run_full_pipeline(
    video_bytes: bytes,
    filename: str,
    segment_duration: int = 30,
) -> Dict[str, Any]:
    """
    Save *video_bytes* to a temp file, run the full analysis pipeline,
    and return the report dict.

    This function is CPU-bound and blocking — always call it inside
    ``asyncio.loop.run_in_executor(None, run_full_pipeline, ...)``.
    """
    # Write upload to a named temp file that persists until we delete it
    suffix = Path(filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(
        suffix=suffix, prefix="nood_upload_", delete=False
    ) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    output_path = tmp_path + "_report.json"

    try:
        from presentation_analyzer import run_pipeline
        report = run_pipeline(
            video_path=tmp_path,
            output_path=output_path,
            segment_duration=segment_duration,
        )
    finally:
        # Clean up temp video; report JSON is optional to keep
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        try:
            os.unlink(output_path)
        except OSError:
            pass

    return report
