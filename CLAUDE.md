# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

**FastAPI backend** (the main entrypoint):
```bash
pip install -r requirements.txt
pip install -r backend/requirements_api.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs
```

**Frontend** (no build, in-browser JSX via Babel):
```bash
python -m http.server 3000   # then open http://localhost:3000
```

**CLI pipeline** (full video analysis → JSON report, bypasses the API):
```bash
python presentation_analyzer.py --video path/to/presentation.mp4
python presentation_analyzer.py --video talk.mp4 --output my_report.json
python presentation_analyzer.py --video talk.mp4 --segment-duration 30
```

**Individual modules** (standalone):
```bash
python "Speech Analysis/speech_analyzer.py" audio.wav --json
python "Speech Analysis/tone_analyzer.py" report.json
python "Speech Analysis/tone_analyzer.py" --demo                    # no real audio needed
python "Body Analysis/body_language_detector.py" --video video.mp4  # opens OpenCV window
```

ffmpeg is required as a system binary (used to extract audio from video).

## Architecture

```
INPUT: video.mp4
    ├── Thread A → Body Analysis/body_language_detector.py
    │              MediaPipe (pose + face landmarks) → TFLite classifier
    │              Output: per-frame emotion + summary dict (9 classes)
    │
    └── Thread B → Speech Analysis/speech_analyzer.py  (stages run sequentially)
                   1. librosa.effects.split → pause ratio (energy-based VAD)
                   2. HuggingFace Whisper → WPM + filler words
                   3. librosa pYIN → pitch/energy variation
                   4. wav2vec2 emotion classifier → vocal emotion
                   │
                   └── Speech Analysis/tone_analyzer.py
                       Pollinations AI free LLM API (no key required)
                       → tone-content appropriateness + coaching tips

MERGE in presentation_analyzer.py: score (40% speech / 30% body / 30% tone) → report.json
```

**Key design decisions:**
- `presentation_analyzer.py` uses `ThreadPoolExecutor(max_workers=2)` to run body and speech+tone in parallel, then merges results.
- **Pipeline resilience**: if one of the two threads crashes, the pipeline still returns a partial report with zero-value defaults for the failed component. The `report["analysis_errors"]` field lists what broke. No all-or-nothing failures.
- **HuggingFace cache redirect**: `Speech Analysis/speech_analyzer.py` sets `HF_HOME` / `HF_HUB_CACHE` / `TRANSFORMERS_CACHE` to a project-local `hf_cache/` folder before any HF import. This sidesteps Windows user-profile cache corruption (OneDrive sync / antivirus interference).
- **VAD**: previously used SpeechBrain's `vad-crdnn-libriparty`, but that model has a SpeechBrain 0.5 / hyperpyyaml version incompatibility. Replaced with `librosa.effects.split(y, top_db=30)` — pure-Python energy-based VAD. No model download. Fast.
- **torchaudio 2.2+ compatibility**: SpeechBrain 0.5.x calls removed functions (`torchaudio.list_audio_backends()`, etc.). The `compat/torchaudio_compat.py` module monkey-patches them back. Files that import SpeechBrain must `import compat.torchaudio_compat` first.
- Audio I/O uses **librosa** (load) and **soundfile** (save) instead of torchaudio to avoid TorchCodec crashes on Windows.
- `body_language_detector.py` uses the new MediaPipe Tasks API (v0.10+). The TFLite model was trained on the old Holistic API output (468 face landmarks × 4 features); the new FaceLandmarker returns 478 landmarks with no visibility field, so the code truncates to 468 and pads visibility with `0.0`.
- The TFLite classifier emits 9 classes: Angry, Confused, Excited, Happy, Pain, Sad, Surprised, Tension, Neutral. The 9th (Neutral) was originally missing from `CLASS_NAMES`, causing `"8"` to leak into reports.
- `tone_analyzer.py` calls `https://text.pollinations.ai/` with `json_mode=True`; no API key needed. Multi-layer JSON parse fallback (outer wrapper → markdown fence stripping → substring extraction).
- Models are downloaded automatically on first run to `hf_cache/` (~1.5 GB total: Whisper-base + wav2vec2 emotion) and `Body Analysis/mediapipe_models/` (~10 MB).
- Scores: speech `overall` is in `[−1, 1]`; body score is in `[0, 1]`; tone fit score is in `[0, 1]`. `compute_overall_score()` normalises speech before the weighted average.

## FastAPI backend

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Returns `{"status":"ok","active_jobs":N}` |
| `POST` | `/api/analyze` | Upload video (`multipart/form-data`, field `file`). Optional query param `segment_duration` (default 30 s). Returns `{"job_id":"...","status":"queued"}` immediately (HTTP 202). |
| `GET`  | `/api/analyze/{job_id}` | Poll job. `status` is `queued→processing→done\|failed`. When `done`, `report` contains the full analysis JSON. |

**Backend structure:**
```
backend/
├── main.py                  FastAPI app + CORS middleware
├── routers/
│   ├── analysis.py          POST /api/analyze, GET /api/analyze/{job_id}
│   └── health.py            GET /health
├── services/
│   ├── job_manager.py       Thread-safe in-memory job store (JobManager singleton)
│   └── pipeline.py          Writes upload to tempfile, calls run_pipeline(), patches sys.path
└── schemas/
    └── analysis.py          Pydantic models for all request/response types
```

**How it works:**
- `POST /api/analyze` reads the upload into memory, creates a `Job` record, then dispatches `_run_and_update()` via `asyncio.loop.run_in_executor(None, ...)` so the event loop is never blocked.
- `pipeline.py` patches `sys.path` once (adding project root, `Body Analysis/`, `Speech Analysis/`) before importing `presentation_analyzer`, so the existing relative imports work unchanged.
- Jobs are stored in `JobManager` (a module-level singleton). On restart all job history is lost — wire up Redis or SQLite for production.

## Frontend

The browser side is plain HTML + JSX, compiled in-browser by Babel Standalone — no `npm install`, no build step.

`index.html` script-tag-includes (in order):
1. `tweaks-panel.jsx` — dev-mode UI panel
2. `src/i18n.jsx` — FR/EN translations
3. `src/data.jsx` — mock REPORT, `API_BASE`, `mapApiReport()`, `window.PENDING_FILE` / `window.LIVE_REPORT` globals
4. `src/components.jsx` — Header, Card, Button, ScoreRing, MiniWaveform, etc.
5. `src/screens/*.jsx` — Landing, Auth, Workspace, Processing, Report, History
6. `src/app.jsx` — top-level router

**Real vs demo mode**:
- Workspace: when user picks a file, `rawFileRef` keeps the actual `File` object. Clicking Analyze sets `window.PENDING_FILE = rawFile` and navigates to Processing.
- Processing: if `window.PENDING_FILE` exists → real upload + poll `/api/analyze`. Otherwise → 60-second fake animation showing the mock report.
- Report: reads from `window.LIVE_REPORT || REPORT` so the same component renders both real and mock data.
- `mapApiReport(api, meta)` in `data.jsx` converts the FastAPI report shape into the frontend's expected shape (handles unit conversions: `filler_rate ×100` for percentages, etc., and unwraps strings into `{fr, en}` for the i18n layer).

## Module locations and path setup

`presentation_analyzer.py` inserts `Body Analysis/` and `Speech Analysis/` into `sys.path` at runtime, so `body_language_detector`, `speech_analyzer`, and `tone_analyzer` are imported by name without package prefixes.

`backend/services/pipeline.py` does the same for the FastAPI side, plus adds the project root.
