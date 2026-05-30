"""
/transcribe endpoint.

Finds the uploaded file by job_id, extracts audio, runs Whisper.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from core.config import settings
from models.schemas import TranscribeRequest, TranscribeResponse
from services.audio_service import extract_audio, SUPPORTED_EXTENSIONS
from services.transcription_service import transcribe

router = APIRouter()
logger = logging.getLogger(__name__)


def _find_upload(job_id: str) -> Path:
    """Locate uploaded file by job_id (any extension)."""
    for ext in SUPPORTED_EXTENSIONS:
        p = settings.uploads_dir / f"{job_id}{ext}"
        if p.exists():
            return p
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No uploaded file found for job_id={job_id}. Did you call /upload first?",
    )


@router.post("/transcribe", response_model=TranscribeResponse, summary="Transcribe audio to Hinglish subtitles")
async def transcribe_audio(body: TranscribeRequest) -> TranscribeResponse:
    """
    Extract audio from the uploaded file and run Whisper transcription.

    - Extracts optimised 16kHz mono WAV using FFmpeg
    - Runs faster-whisper (Large v3) in Hinglish mode
    - Returns timed subtitle segments

    **Note:** First call loads the Whisper model (~10–30s on cold start).
    Subsequent calls are much faster.
    """
    upload_path = _find_upload(body.job_id)

    # Step 1 — Extract audio
    try:
        audio_path = extract_audio(upload_path, settings.audio_dir)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio extraction failed: {e}",
        )

    # Step 2 — Transcribe
    try:
        segments = transcribe(audio_path, language=body.language)
    except Exception as e:
        logger.exception("Transcription error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {e}",
        )

    duration = segments[-1].end if segments else 0.0
    word_count = sum(len(s.text.split()) for s in segments)

    return TranscribeResponse(
        job_id=body.job_id,
        segments=segments,
        detected_language=body.language,
        duration_seconds=round(duration, 2),
        word_count=word_count,
    )
