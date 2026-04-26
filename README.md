# NOOD — AI Presentation Coach

NOOD analyzes a video of someone giving a presentation and grades them across three dimensions:
- **Body language** — emotion detection from face + pose landmarks
- **Speech** — speaking rate, filler words, pitch variation, energy, pauses, vocal emotion
- **Tone–content fit** — does the delivery match what's being said?

It returns a JSON report and a 0–100 overall score with a letter grade. The frontend renders this as an interactive dashboard with a video player, timeline, and coaching tips.

---

## Architecture at a glance

```
┌──────────────┐                ┌──────────────────────┐
│   Browser    │  POST video    │   FastAPI backend    │
│  (HTML/JSX)  │ ───────────▶   │     (port 8000)      │
│              │  poll job_id   │                      │
│              │ ◀───────────── │                      │
└──────────────┘                └──────────┬───────────┘
                                           │
                                           ▼
                                ┌──────────────────────┐
                                │ presentation_         │
                                │  analyzer.py          │
                                │  (orchestrator)       │
                                └──┬────────────────┬──┘
                                   │ ThreadPool ×2  │
                       ┌───────────▼──┐         ┌───▼──────────────┐
                       │ Body         │         │ Speech           │
                       │ Analysis     │         │ Analysis         │
                       │              │         │                  │
                       │ MediaPipe +  │         │ librosa VAD      │
                       │ TFLite       │         │ Whisper ASR      │
                       │ (9 emotions) │         │ pYIN prosody     │
                       │              │         │ wav2vec2 emotion │
                       └──────────────┘         └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │ Tone Analysis   │
                                                │ (Pollinations   │
                                                │  free LLM API)  │
                                                └─────────────────┘
```

**Scoring**: 40 % speech + 30 % body + 30 % tone → 0–100 score → letter grade (A ≥ 85, B ≥ 70, C ≥ 55, D ≥ 40, F < 40).

---

## Project layout

```
nood/
├── backend/                     FastAPI server (the HTTP API)
│   ├── main.py                  app entry, CORS
│   ├── routers/analysis.py      POST /api/analyze, GET /api/analyze/{job_id}
│   ├── routers/health.py        GET /health
│   ├── services/pipeline.py     wraps presentation_analyzer in a thread pool
│   ├── services/job_manager.py  in-memory job store (singleton)
│   └── schemas/analysis.py      Pydantic request/response models
│
├── Body Analysis/               Body-language emotion detector
│   ├── body_language_detector.py
│   ├── body_language.tflite     trained model (9 classes)
│   └── mediapipe_models/        downloaded on first run (~10 MB)
│
├── Speech Analysis/             Speech + tone analyzers
│   ├── speech_analyzer.py       VAD + ASR + prosody + vocal emotion
│   └── tone_analyzer.py         calls Pollinations LLM API
│
├── compat/torchaudio_compat.py  monkey-patch for torchaudio 2.2+
│
├── src/                         Frontend (no build step — JSX in browser via Babel)
│   ├── i18n.jsx                 FR/EN translations
│   ├── data.jsx                 mock data + API_BASE + mapApiReport()
│   ├── components.jsx           Header, Card, Button, ScoreRing, etc.
│   ├── app.jsx                  router
│   └── screens/                 Landing, Auth, Workspace, Processing, Report, History
│
├── assets/                      logo + hero images
├── data/                        sample report JSONs
├── diagrams/                    architecture SVGs
├── samples/                     local test videos (gitignored)
├── hf_cache/                    HuggingFace model cache (gitignored, ~1.5 GB after first run)
├── pretrained_models/           legacy SpeechBrain cache (gitignored)
│
├── presentation_analyzer.py     pipeline orchestrator (CLI entrypoint too)
├── index.html                   frontend entry (loads all .jsx via Babel)
├── tweaks-panel.jsx             dev-mode UI panel
├── requirements.txt             pinned ML deps
├── backend/requirements_api.txt FastAPI deps
├── Dockerfile                   container image
├── .dockerignore
├── .gitignore
├── CLAUDE.md                    deeper architecture notes for AI assistants
├── reference.md                 detailed per-module reference
└── README.md                    you are here
```

---

## Run it locally

### Prerequisites
- **Python 3.11** (3.10 also works)
- **ffmpeg** as a system binary (used to extract audio from video)
  - Windows: `winget install ffmpeg` or download from https://ffmpeg.org
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`
- ~3 GB free disk for the ML models (downloaded on first analysis)

### Install dependencies
```bash
pip install -r requirements.txt
pip install -r backend/requirements_api.txt
```

### Start the backend
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Visit http://localhost:8000/docs for the auto-generated Swagger UI.
Visit http://localhost:8000/health to check it's alive.

### Start the frontend (separate terminal)
```bash
python -m http.server 3000
```
Open http://localhost:3000 in your browser.

> The frontend is plain HTML + JSX compiled in-browser by Babel — **no `npm install`, no build step**. Just serve the folder over HTTP (you can't open `index.html` via `file://` because of CORS).

### First-run notes
The first video you analyze triggers downloads of:
- `openai/whisper-base` (~140 MB) — speech-to-text
- `ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition` (~1.2 GB) — vocal emotion
- MediaPipe pose + face landmarker (~10 MB)

These are cached in `hf_cache/` and `Body Analysis/mediapipe_models/`. Subsequent runs are fast.

---

## API reference

### `GET /health`
```json
{ "status": "ok", "active_jobs": 0 }
```

### `POST /api/analyze`
Multipart form upload.

| Field | Type | Description |
|-------|------|-------------|
| `file` | binary | Video file (mp4, mkv, mov, avi, webm, flv, wmv) |
| `segment_duration` | int (query, optional) | Speech segment window in seconds (default 30) |

**Response (HTTP 202)**:
```json
{ "job_id": "a050e202-605f-411c-9d89-a65554137950", "status": "queued" }
```

### `GET /api/analyze/{job_id}`
Poll for status. Returns `queued` → `processing` → `done` (with full `report`) or `failed` (with `error`).

```json
{
  "job_id": "...",
  "status": "done",
  "report": {
    "overall_score": 72.5,
    "overall_grade": "B",
    "component_scores": { "speech_score": ..., "body_language_score": ..., "tone_fit_score": ... },
    "body_language": { ... },
    "speech": { ... },
    "tone": { ... },
    "timeline": [ ... ],
    "analysis_errors": {}
  }
}
```

If one analyzer crashed, that component's scores are zero and `analysis_errors` lists what failed — the report is still produced (no all-or-nothing failure).

---

## CLI usage (skip the API)

```bash
python presentation_analyzer.py --video samples/sample_video.mp4
python presentation_analyzer.py --video talk.mp4 --output my_report.json
python presentation_analyzer.py --video talk.mp4 --segment-duration 30
```

Individual modules also run standalone:

```bash
python "Speech Analysis/speech_analyzer.py" audio.wav --json
python "Speech Analysis/tone_analyzer.py" --demo            # no real audio
python "Body Analysis/body_language_detector.py" --video v.mp4   # opens OpenCV window
```

---

## Run with Docker

```bash
docker build -t nood-backend .
docker volume create nood_models
docker run -d --name nood -p 8000:8000 -v nood_models:/app/hf_cache nood-backend
```

The volume is essential — without it, the container re-downloads ~1.5 GB of models every restart.

For deployment to Oracle Cloud (or any other VPS), see the deployment notes in `reference.md`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ffmpeg not found` | system binary missing | Install ffmpeg, ensure it's on PATH |
| `[ERROR] body_language_detector failed` | no person/face visible in video | Use a video with a clearly visible speaker |
| HuggingFace cache permission errors on Windows | corrupted cache folders | The project sets `HF_HOME` to local `hf_cache/`, not user profile — should not happen, but if it does, `rm -rf hf_cache/` and let it re-download |
| Frontend shows mock data with no real upload | `window.PENDING_FILE` is null | Click "Analyze" with a real file picked, not "Try a sample" |
| Browser blocks API calls (CORS) | backend not running | Start uvicorn first; check `/health` endpoint |
| Backend serves but long pause then 500 | LLM tone analysis API timed out | Pollinations sometimes 30s+; the pipeline still returns body+speech if tone fails |

---

## License

See `LICENSE` (MIT).
