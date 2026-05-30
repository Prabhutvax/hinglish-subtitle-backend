"""
Re-segmentation service.

Splits long Whisper segments into shorter, readable subtitle chunks
based on a user-selected words-per-subtitle setting.

This is the #1 launch feature — Whisper often returns 10–15 word
segments that are too long for Reels/Shorts. This breaks them into
3–6 word chunks with proportionally distributed timestamps.
"""
import logging
from models.schemas import SubtitleSegment

logger = logging.getLogger(__name__)

# Sentinel value for "auto" mode
AUTO = "auto"


def _words_per_segment_auto(text: str) -> int:
    """
    Pick a sensible default based on segment length.
    Short segments → keep as-is (4 words).
    Long segments → split at 4 words.
    """
    word_count = len(text.split())
    if word_count <= 5:
        return word_count          # don't split tiny segments further
    return 4                       # default for auto


def resegment(
    segments: list[SubtitleSegment],
    words_per_subtitle: int | str = 4,
) -> list[SubtitleSegment]:
    """
    Split all segments so each subtitle contains at most
    `words_per_subtitle` words. Timestamps are distributed
    proportionally across the new chunks.

    Args:
        segments: Raw Whisper segments (may have 10–20 words each)
        words_per_subtitle: int (3–6) or "auto"

    Returns:
        New list of SubtitleSegment with correct indices and timestamps.
    """
    result: list[SubtitleSegment] = []
    new_index = 0

    for seg in segments:
        text = seg.text.strip()
        words = text.split()
        total_words = len(words)
        duration = seg.end - seg.start

        # Determine chunk size for this segment
        if words_per_subtitle == AUTO or words_per_subtitle == "auto":
            chunk_size = _words_per_segment_auto(text)
        else:
            chunk_size = int(words_per_subtitle)

        # If segment already fits in one chunk, keep it as-is
        if total_words <= chunk_size:
            result.append(SubtitleSegment(
                index=new_index,
                start=round(seg.start, 3),
                end=round(seg.end, 3),
                text=text,
            ))
            new_index += 1
            continue

        # Split into chunks and distribute time proportionally
        chunks: list[list[str]] = []
        for i in range(0, total_words, chunk_size):
            chunks.append(words[i : i + chunk_size])

        # Time per word (uniform distribution within segment)
        time_per_word = duration / total_words

        word_cursor = 0
        for chunk in chunks:
            chunk_start = seg.start + word_cursor * time_per_word
            chunk_end = chunk_start + len(chunk) * time_per_word
            # Clamp last chunk to segment end to avoid float drift
            chunk_end = min(chunk_end, seg.end)

            result.append(SubtitleSegment(
                index=new_index,
                start=round(chunk_start, 3),
                end=round(chunk_end, 3),
                text=" ".join(chunk),
            ))
            new_index += 1
            word_cursor += len(chunk)

        logger.debug(
            f"Segment {seg.index} ({total_words}w) → {len(chunks)} chunks "
            f"@ {chunk_size}w each"
        )

    logger.info(
        f"Re-segmentation complete: {len(segments)} → {len(result)} segments "
        f"(words_per_subtitle={words_per_subtitle})"
    )
    return result
