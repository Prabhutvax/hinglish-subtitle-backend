# Hinglish Subtitle Creator — Backend

FastAPI backend. Upload video → Whisper transcription → SRT download.

---

## Quick Start (Local)

```bash
# 1. Install FFmpeg
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian

# 2. Setup Python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit WHISPER_MODEL if needed (see below)

# 4. Run
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** — interactive API docs.

---

## API Pipeline

```
POST /upload          →  { job_id }
POST /transcribe      →  { segments: [...] }
POST /resegment       →  { segments: [...] }   ← splits long lines
POST /export          →  { download_url }       ← resegment runs here too
GET  /download/{file} →  SRT file download
```

### Minimal flow (2 calls)

```bash
# Upload
curl -X POST http://localhost:8000/upload -F "file=@video.mp4"
# → { "job_id": "abc123", ... }

# Export directly (transcribes + re-segments + exports in one shot)
# Actually: transcribe first, then export:

# 1. Transcribe
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"job_id":"abc123","language":"hi"}'

# 2. Export SRT (re-segmentation runs automatically at 4 words/line)
curl -X POST http://localhost:8000/export \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123",
    "segments": [...],
    "format": "srt",
    "words_per_subtitle": "4"
  }'

# 3. Download
curl -O http://localhost:8000/download/abc123.srt
```

---

## Re-segmentation

This is the key readability feature.

Whisper outputs: `"This is a very long subtitle segment that is difficult to read"` (1 segment)

With `words_per_subtitle: "4"` → 4 segments:
```
This is a very
long subtitle segment
that is difficult
to read
```

Timestamps are distributed proportionally across chunks.

**Options:** `"auto"` | `"3"` | `"4"` (default) | `"5"` | `"6"`

---

## Whisper Model Guide

| Model | RAM needed | Speed on CPU | Accuracy |
|---|---|---|---|
| `tiny` | 1 GB | Very fast | Poor |
| `base` | 1 GB | Fast | OK |
| `small` | 2 GB | Medium | Good |
| `medium` | 5 GB | Slow | Very good |
| `large-v3` | 6 GB | Very slow | Best |

**For local dev:** `medium` with `WHISPER_COMPUTE_TYPE=int8`
**For production GPU:** `large-v3` with `WHISPER_COMPUTE_TYPE=float16`

---

## Deployment

### Option A — Railway (recommended for launch)

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Set environment variables (copy from `.env.production`)
4. Deploy — Railway auto-detects the Dockerfile

**Cost:** ~$5–10/month for a 512MB RAM instance (use `small` model here).

### Option B — Docker (any VPS)

```bash
docker build -t hinglish-backend .
docker run -p 8000:8000 \
  -e WHISPER_MODEL=medium \
  -e WHISPER_DEVICE=cpu \
  -v $(pwd)/temp:/app/temp \
  hinglish-backend
```

### Option C — Render

1. Connect GitHub repo on [render.com](https://render.com)
2. Select "Web Service" → Docker
3. Add env vars from `.env.production`
4. Deploy

---

## Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `WHISPER_MODEL` | `large-v3` | Use `medium` on CPU |
| `WHISPER_DEVICE` | `auto` | `cpu` or `cuda` |
| `WHISPER_COMPUTE_TYPE` | `auto` | `int8` for CPU, `float16` for GPU |
| `MAX_UPLOAD_SIZE_MB` | `500` | Max file size |
| `PORT` | `8000` | Server port |
| `DEBUG` | `true` | Set `false` in production |

---

## Project Structure

```
hinglish-backend/
├── main.py                         # App entry point
├── requirements.txt
├── Dockerfile
├── railway.toml                    # Railway deployment config
├── .env.example
├── .env.production                 # Production env template
├── core/
│   └── config.py                   # Settings
├── models/
│   └── schemas.py                  # Request/response types
├── services/
│   ├── audio_service.py            # FFmpeg audio extraction
│   ├── transcription_service.py    # Whisper Large v3
│   ├── resegment_service.py        # ★ Words-per-subtitle splitting
│   ├── subtitle_service.py         # SRT + ASS file generation
│   └── export_service.py           # Export pipeline
└── api/routes/
    ├── upload.py
    ├── transcribe.py
    ├── resegment.py                # ★ New endpoint
    └── export.py
```
