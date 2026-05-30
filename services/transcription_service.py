"""
Whisper transcription service.

Uses faster-whisper (CTranslate2 backend) with Whisper Large v3.
Configured for Hindi-English (Hinglish) mixed speech.
Model is loaded once and cached — subsequent calls reuse it.
"""
import logging
from pathlib import Path
from functools import lru_cache
from typing import Generator

from faster_whisper import WhisperModel

from core.config import settings
from models.schemas import SubtitleSegment

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model() -> WhisperModel:
    """Load and cache Whisper model. Called once on first transcription."""
    device = settings.whisper_device
    compute_type = settings.whisper_compute_type

    # Auto-select best available device/precision
    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    logger.info(
        f"Loading Whisper model '{settings.whisper_model}' "
        f"on {device} with {compute_type} precision..."
    )

    model = WhisperModel(
        settings.whisper_model,
        device=device,
        compute_type=compute_type,
    )
    logger.info("Whisper model loaded ✓")
    return model


def transcribe(audio_path: Path, language: str = "hi") -> list[SubtitleSegment]:
    """
    Transcribe audio file and return timed subtitle segments.

    language="hi" tells Whisper to expect Hindi — it handles
    Hinglish (Hindi + English mixed) well in this mode.

    Returns a list of SubtitleSegment objects with start/end times.
    """
    model = _load_model()

    logger.info(f"Transcribing {audio_path} (language={language})")

    segments_gen, info = model.transcribe(
        str(audio_path),
        language=language,
        task="transcribe",
        beam_size=1,
        best_of=1,
        vad_filter=True,            # Voice Activity Detection — skip silences
        vad_parameters={
            "min_silence_duration_ms": 500,
            "threshold": 0.4,
        },
        word_timestamps=False,      # segment-level timestamps are sufficient for MVP
        condition_on_previous_text=True,
    )

    logger.info(
        f"Detected language: {info.language} "
        f"(confidence: {info.language_probability:.2f})"
    )

    results: list[SubtitleSegment] = []
    for i, seg in enumerate(segments_gen):
        text = seg.text.strip()
        if not text:
            continue
        results.append(SubtitleSegment(
            index=i,
            start=round(seg.start, 3),
            end=round(seg.end, 3),
            text=text,
        ))
        logger.debug(f"  [{seg.start:.1f}s → {seg.end:.1f}s] {text}")

    logger.info(f"Transcription complete — {len(results)} segments")
    return results


def get_detected_language(audio_path: Path) -> str:
    """Quick language detection without full transcription."""
    model = _load_model()
    _, info = model.transcribe(str(audio_path), language=None, duration=30)
    return info.language
