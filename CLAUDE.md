# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

**CLI pipeline** (full video analysis → JSON report):
```bash
python presentation_analyzer.py --video path/to/presentation.mp4
python presentation_analyzer.py --video talk.mp4 --output my_report.json
python presentation_analyzer.py --video talk.mp4 --segment-duration 30
```

**Streamlit web app** (upload video via browser):
```bash
cd "Streamlit + Whisper"
streamlit run streamlit_app.py
# Opens at http://localhost:8501
```

**Individual modules** (standalone):
```bash
# Speech analysis only
python "Speech Analysis/speech_analyzer.py" audio.wav
python "Speech Analysis/speech_analyzer.py" audio.wav --segment-duration 30 --json

# Tone analysis only (needs a speech_analyzer JSON output)
python "Speech Analysis/tone_analyzer.py" report.json
python "Speech Analysis/tone_analyzer.py" --demo   # no real audio needed

# Body language only (shows OpenCV GUI window)
python "Body Analysis/body_language_detector.py" --video video.mp4
```

**Install dependencies:**
```bash
pip install -r requirements.txt
# Also requires ffmpeg as a system binary (used by presentation_analyzer.py to extract audio)
```

## Architecture

The project is a presentation performance analyzer with two entry points sharing the same analysis modules:

```
INPUT: video.mp4
    ├── Thread A → Body Analysis/body_language_detector.py
    │              MediaPipe (pose + face landmarks) → TFLite classifier
    │              Output: per-frame emotion + summary dict
    │
    └── Thread B → Speech Analysis/speech_analyzer.py  (stages run sequentially)
                   1. VAD (SpeechBrain) → pause ratio
                   2. ASR (SpeechBrain wav2vec2) → WPM + filler words
                   3. librosa pYIN → pitch/energy variation
                   4. SpeechBrain emotion classifier → vocal emotion
                   │
                   └── Speech Analysis/tone_analyzer.py
                       Pollinations AI free LLM API (no key required)
                       → tone-content appropriateness + coaching tips

MERGE in presentation_analyzer.py: score (40% speech / 30% body / 30% tone) → report.json
```

**Key design decisions:**
- `presentation_analyzer.py` uses `ThreadPoolExecutor(max_workers=2)` to run body and speech+tone analyses in parallel, then merges results.
- **torchaudio 2.2+ compatibility:** SpeechBrain 0.5.x calls removed functions (`torchaudio.list_audio_backends()`, etc.). The `compat/torchaudio_compat.py` module monkey-patches them back. All files that import SpeechBrain must `import compat.torchaudio_compat` first.
- Audio I/O uses **librosa** (load) and **soundfile** (save) instead of torchaudio to avoid TorchCodec crashes on Windows.
- SpeechBrain models require 16 kHz mono WAV; `speech_analyzer.py` writes a `_16k_tmp.wav` temp file alongside the input before invoking SpeechBrain, then deletes it.
- `body_language_detector.py` uses the new MediaPipe Tasks API (v0.10+). The TFLite model was trained on the old Holistic API output (468 face landmarks × 4 features); the new FaceLandmarker returns 478 landmarks with no visibility field, so the code truncates to 468 and pads visibility with `0.0`.
- `tone_analyzer.py` calls `https://text.pollinations.ai/` with `json_mode=True`; no API key needed. It has a multi-layer JSON parse fallback (outer wrapper → markdown fence stripping → substring extraction).
- Models are downloaded automatically on first run to `pretrained_models/` (~1–2 GB total for ASR + VAD) and `Body Analysis/mediapipe_models/`.
- Scores: speech `overall` is in `[−1, 1]`; body score is in `[0, 1]`; tone fit score is in `[0, 1]`. `compute_overall_score()` normalises speech before the weighted average.

**Streamlit app** (`Streamlit + Whisper/`) is a separate, simplified frontend. It calls `combined_analyzer.py` (not `presentation_analyzer.py`) and focuses on grammar/vocabulary/fluency feedback via the language-and-content analyzer rather than the full prosody+body pipeline.

## FastAPI backend

**Start the API server** (from the `NOOD` project root):
```bash
pip install -r backend/requirements_api.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs
```

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Returns `{"status":"ok","active_jobs":N}` |
| `POST` | `/api/analyze` | Upload video (`multipart/form-data`, field `file`). Optional query param `segment_duration` (default 30 s). Returns `{"job_id":"...","status":"queued"}` immediately (HTTP 202). |
| `GET`  | `/api/analyze/{job_id}` | Poll job. `status` is `queued→processing→done|failed`. When `done`, `report` contains the full analysis JSON. |

**Backend structure:**
```
backend/
├── main.py                  # FastAPI app + CORS middleware
├── routers/
│   ├── analysis.py          # POST /api/analyze, GET /api/analyze/{job_id}
│   └── health.py            # GET /health
├── services/
│   ├── job_manager.py       # Thread-safe in-memory job store (JobManager singleton)
│   └── pipeline.py          # Writes upload to tempfile, calls run_pipeline(), patches sys.path
└── schemas/
    └── analysis.py          # Pydantic models for all request/response types
```

**How it works:**
- `POST /api/analyze` reads the upload into memory, creates a `Job` record, then dispatches `_run_and_update()` via `asyncio.loop.run_in_executor(None, ...)` so the event loop is never blocked.
- `pipeline.py` patches `sys.path` once (adding project root, `Body Analysis/`, `Speech Analysis/`) before importing `presentation_analyzer`, so the existing relative imports work unchanged.
- Jobs are stored in `JobManager` (a module-level singleton). On restart all job history is lost — wire up a persistent store (Redis, SQLite) if needed.

## Module locations and path setup

`presentation_analyzer.py` inserts `Body Analysis/` and `Speech Analysis/` into `sys.path` at runtime, so `body_language_detector`, `speech_analyzer`, and `tone_analyzer` are imported by name without package prefixes.

The Streamlit app does the same for its own sibling modules in `Streamlit + Whisper/`.
