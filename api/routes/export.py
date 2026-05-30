"""
/export endpoint.

Before exporting, optionally runs re-segmentation so the final
SRT always has the right words-per-subtitle length.

Generates: SRT, ASS, MP4 with burned subtitles, or ZIP of all.
"""
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from core.config import settings
from models.schemas import ExportRequest, ExportResponse, ExportFormat
from services.audio_service import SUPPORTED_EXTENSIONS
from services.resegment_service import resegment
from services import export_service

router = APIRouter()
logger = logging.getLogger(__name__)


MIME_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".srt": "text/plain; charset=utf-8",
    ".ass": "text/plain; charset=utf-8",
    ".zip": "application/zip",
}


def _find_upload(job_id: str) -> Path:
    for ext in SUPPORTED_EXTENSIONS:
        p = settings.uploads_dir / f"{job_id}{ext}"
        if p.exists():
            return p
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No uploaded file for job_id={job_id}",
    )


@router.post("/export", response_model=ExportResponse, summary="Export subtitled video or subtitle files")
async def export_video(body: ExportRequest) -> ExportResponse:
    """
    Export the final output.

    Pipeline (in order):
    1. Optionally re-segment to words_per_subtitle length
    2. Generate SRT / ASS / MP4 with burned subtitles

    **format options:**
    - `srt` — plain SubRip (default, recommended for launch)
    - `ass` — styled Advanced SubStation Alpha
    - `mp4` — MP4 with subtitles burned in via FFmpeg libass
    - `all` — ZIP containing all three

    **words_per_subtitle:** `"auto"` | `"3"` | `"4"` | `"5"` | `"6"`
    Applied before export. Default: `"4"`.
    """
    segments = body.segments

    # ── Step 1: Re-segment if requested ──────────────────────────────────────
    if body.apply_resegment and segments:
        segments = resegment(segments, words_per_subtitle=body.words_per_subtitle)
        logger.info(
            f"Re-segmented {len(body.segments)} → {len(segments)} segments "
            f"(words={body.words_per_subtitle})"
        )

    # ── Step 2: Export ────────────────────────────────────────────────────────
    # For SRT-only exports we don't need the original video file
    needs_video = body.format in (ExportFormat.mp4, ExportFormat.all)

    video_path: Path | None = None
    if needs_video:
        video_path = _find_upload(body.job_id)

    try:
        output_path = export_service.export(
            job_id=body.job_id,
            video_path=video_path,
            segments=segments,
            style_options=body.style,
            export_format=body.format,
            output_dir=settings.outputs_dir,
            quality=body.video_quality,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    download_url = f"/download/{output_path.name}"

    return ExportResponse(
        job_id=body.job_id,
        format=body.format,
        download_url=download_url,
        file_size_bytes=output_path.stat().st_size,
        segment_count=len(segments),
        message=f"Export complete — {len(segments)} subtitle segments. Download: {download_url}",
    )


@router.get("/download/{filename}", summary="Download exported file")
async def download_file(filename: str) -> FileResponse:
    """Download an exported file by filename."""
    # Basic path traversal protection
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    file_path = settings.outputs_dir / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}",
        )

    suffix = file_path.suffix.lower()
    media_type = MIME_TYPES.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )
