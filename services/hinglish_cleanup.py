"""
Hinglish Cleanup Layer.

Post-processing pipeline for Whisper output:
  1. Capitalize first letter of each segment
  2. Normalize common Hinglish spelling variants
  3. Optionally remove filler words
  4. Preserve slang (don't over-correct informal words)

This module is intentionally simple and rule-based for the MVP.
It's designed to be swapped out for an LLM-based layer later —
just replace `clean_segment()` with an API call to Claude/GPT.
"""
import re
import logging

from models.schemas import SubtitleSegment, CleanupOptions

logger = logging.getLogger(__name__)


# ── Spelling normalization map ────────────────────────────────────────────────
# Maps common Whisper mis-spellings / variants → preferred Hinglish spellings.
# Add more as you encounter them in your content.
SPELLING_MAP: dict[str, str] = {
    # bohot / bahut
    r"\bbohut\b": "bahut",
    r"\bbahot\b": "bahut",
    r"\bbohot\b": "bahut",
    # karo / karna
    r"\bkarro\b": "karo",
    r"\bkarnaa\b": "karna",
    # nahi / nahin
    r"\bnahin\b": "nahi",
    r"\bnahi n\b": "nahi",
    # aaj / aajkal
    r"\baaj kal\b": "aajkal",
    # yaar
    r"\byar\b": "yaar",
    # bhai
    r"\bbhi\b(?! )": "bhai",   # only standalone "bhi" not "bhi " (also = "also")
    # kya
    r"\bkia\b": "kya",
    # toh / to
    r"\btho\b": "toh",
    # agar
    r"\bagar\b": "agar",        # already correct but normalize case
    # dekho
    r"\bdekh o\b": "dekho",
    # samajh
    r"\bsamaj\b": "samajh",
    # theek
    r"\btheek\b": "theek",
    r"\bthik\b": "theek",
    r"\bthek\b": "theek",
    # mazaa / maza
    r"\bmaza\b": "mazaa",
    # subscribe
    r"\bsubscribe\b": "subscribe",   # already correct, ensures lowercase
}

# ── Filler words ──────────────────────────────────────────────────────────────
FILLER_PATTERNS: list[str] = [
    r"\bum+\b",
    r"\buh+\b",
    r"\bhmm+\b",
    r"\bahh+\b",
    r"\berr+\b",
    r"\blike\b(?=\s+\blike\b)",  # duplicate "like like"
    r"\byou know\b",
    r"\bi mean\b",
    r"\bbasically\b(?=\s)",      # only as sentence-level filler
]

# ── Slang words to preserve (never touch these) ───────────────────────────────
PRESERVE_SLANG: set[str] = {
    "bro", "yaar", "bhai", "dude", "boss", "ngl", "lol", "wtf",
    "omg", "bruh", "guys", "isko", "usko", "toh", "aur", "kya",
    "sahi", "bilkul", "bas", "chalo", "haan", "nahi", "arre",
    "accha", "theek", "mazaa", "bindaas", "jhakkas", "ekdum",
}


def _capitalize_first(text: str) -> str:
    """Capitalize only the very first character, leave the rest alone."""
    return text[0].upper() + text[1:] if text else text


def _normalize_spelling(text: str) -> str:
    """Apply the spelling normalization map (case-insensitive)."""
    for pattern, replacement in SPELLING_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _remove_fillers(text: str) -> str:
    """Remove common filler words/sounds."""
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    # Clean up double spaces left behind
    text = re.sub(r" {2,}", " ", text).strip()
    return text


def _strip_leading_punctuation(text: str) -> str:
    """Whisper sometimes starts segments with ',' or '-'."""
    return re.sub(r"^[,\-\s]+", "", text)


def clean_segment(text: str, options: CleanupOptions) -> str:
    """
    Apply the full cleanup pipeline to a single subtitle text.

    This is the function to replace with an LLM call for smarter cleanup.
    Signature should stay the same: str → str.
    """
    text = _strip_leading_punctuation(text)

    if options.normalize_spelling:
        text = _normalize_spelling(text)

    if options.remove_fillers:
        text = _remove_fillers(text)

    if options.auto_capitalize:
        text = _capitalize_first(text)

    return text.strip()


def process_segments(
    segments: list[SubtitleSegment],
    options: CleanupOptions,
) -> tuple[list[SubtitleSegment], int]:
    """
    Run the cleanup pipeline over all segments.

    Returns (cleaned_segments, number_of_changes).
    """
    cleaned: list[SubtitleSegment] = []
    changes = 0

    for seg in segments:
        original = seg.text
        cleaned_text = clean_segment(original, options)

        if cleaned_text != original:
            changes += 1
            logger.debug(f"Cleaned: '{original}' → '{cleaned_text}'")

        cleaned.append(SubtitleSegment(
            index=seg.index,
            start=seg.start,
            end=seg.end,
            text=cleaned_text,
        ))

    logger.info(f"Hinglish cleanup done — {changes}/{len(segments)} segments modified")
    return cleaned, changes
