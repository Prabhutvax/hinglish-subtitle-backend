"""
Hinglish Subtitle Creator — FastAPI Backend
============================================

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from api.routes import upload, transcribe, resegment, export

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Startup ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp dirs ready under: {settings.temp_dir.resolve()}")
    logger.info(f"Whisper model: {settings.whisper_model} | device: {settings.whisper_device}")
    yield
    logger.info("Shutdown.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Hinglish Subtitle Creator API",
    description="""
## Hinglish Subtitle Creator — Backend API

Upload a video, get readable subtitles, download SRT. Built for Indian content creators.

### Pipeline
1. **POST /upload** — Upload MP4/MOV/MP3/WAV
2. **POST /transcribe** — Whisper Large v3 → timed segments
3. **POST /resegment** — Split into short subtitle lines (3–6 words)
4. **POST /export** — Download SRT (or MP4 with burned subtitles)

### Quick start
Upload → Transcribe → Export (resegment runs automatically inside export).
""",
    version="1.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",        # Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(upload.router,     tags=["1. Upload"])
app.include_router(transcribe.router, tags=["2. Transcribe"])
app.include_router(resegment.router,  tags=["3. Re-segment"])
app.include_router(export.router,     tags=["4. Export"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Hinglish Subtitle Creator API",
        "version": "1.1.0",
        "status": "running",
        "docs": "/docs",
        "whisper_model": settings.whisper_model,
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
