"""
/resegment endpoint.

Splits long Whisper segments into shorter subtitle chunks
based on words-per-subtitle preference (3, 4, 5, 6, or auto).

This is a pure text + timestamp operation — no audio/video needed.
"""
import logging

from fastapi import APIRouter

from models.schemas import ResegmentRequest, ResegmentResponse
from services.resegment_service import resegment

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/resegment",
    response_model=ResegmentResponse,
    summary="Split long segments into short subtitle chunks",
)
async def resegment_subtitles(body: ResegmentRequest) -> ResegmentResponse:
    """
    Re-segment Whisper output into shorter, readable subtitle lines.

    Whisper tends to produce long segments (10–15 words). This endpoint
    splits them to the creator's preferred length with proportionally
    distributed timestamps.

    **words_per_subtitle options:**
    - `auto` — smart default based on segment length
    - `3` — very punchy, best for fast-paced content
    - `4` — recommended default for Reels/Shorts
    - `5` — balanced
    - `6` — longer lines, good for slower speech
    """
    original_count = len(body.segments)

    new_segments = resegment(
        segments=body.segments,
        words_per_subtitle=body.words_per_subtitle.value,
    )

    return ResegmentResponse(
        job_id=body.job_id,
        segments=new_segments,
        original_count=original_count,
        new_count=len(new_segments),
        words_per_subtitle=body.words_per_subtitle.value,
    )
