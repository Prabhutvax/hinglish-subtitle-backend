"""
/generate-subtitles endpoint.

Applies the Hinglish cleanup layer to raw Whisper segments.
This is a pure text processing step — no audio/video needed.
"""
import logging

from fastapi import APIRouter

from models.schemas import GenerateSubtitlesRequest, GenerateSubtitlesResponse
from services.hinglish_cleanup import process_segments

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/generate-subtitles",
    response_model=GenerateSubtitlesResponse,
    summary="Apply Hinglish cleanup layer to raw transcription",
)
async def generate_subtitles(body: GenerateSubtitlesRequest) -> GenerateSubtitlesResponse:
    """
    Apply the Hinglish post-processing pipeline to raw Whisper output.

    Cleanup steps (configurable via `cleanup` options):
    - **auto_capitalize**: Capitalize first letter of each segment
    - **normalize_spelling**: Fix common Hinglish spelling variants (bohot→bahut, etc.)
    - **remove_fillers**: Remove um, uh, hmm, "you know", etc.
    - **preserve_slang**: Protect informal words from over-correction

    Returns cleaned segments ready for editing or export.
    """
    cleaned_segments, changes_made = process_segments(body.segments, body.cleanup)

    return GenerateSubtitlesResponse(
        job_id=body.job_id,
        segments=cleaned_segments,
        changes_made=changes_made,
    )
