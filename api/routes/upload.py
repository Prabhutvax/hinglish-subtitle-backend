"""
/upload endpoint.

Accepts video/audio files, saves to disk, returns a job_id
that is used in all subsequent API calls.
"""
import uuid
import logging
import aiofiles
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status

from core.config import settings
from models.schemas import UploadResponse
from services.audio_service import is_supported, get_media_duration

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadResponse, summary="Upload video or audio file")
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a video or audio file.

    Returns a `job_id` that must be passed to all subsequent API calls
    (/transcribe, /generate-subtitles, /export).
    """
    # Validate extension
    if not is_supported(file.filename or ""):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Supported: MP4, MOV, MP3, WAV, M4A, WebM, MKV",
        )

    # Read & check size
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb} MB",
        )

    # Generate job ID and save file
    job_id = str(uuid.uuid4())
    suffix = Path(file.filename or "upload.mp4").suffix.lower()
    save_path = settings.uploads_dir / f"{job_id}{suffix}"
    save_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(content)

    # Get duration (best-effort)
    try:
        duration = get_media_duration(save_path)
    except Exception:
        duration = None

    logger.info(f"Uploaded: {file.filename} → {save_path} (job_id={job_id})")

    return UploadResponse(
        job_id=job_id,
        filename=file.filename or "upload",
        size_bytes=len(content),
        duration_seconds=duration,
        message="File uploaded successfully. Use job_id in /transcribe.",
    )
