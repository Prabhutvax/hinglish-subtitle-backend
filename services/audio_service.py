"""
Audio extraction service.

Extracts audio from uploaded video/audio files using FFmpeg,
optimises the result for Whisper transcription (16kHz mono WAV).
"""

import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported input formats
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mp3", ".wav", ".m4a", ".webm", ".mkv"}


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def extract_audio(input_path: Path, output_dir: Path) -> Path:
    """
    Extract and optimise audio from input_path.

    Output: 16kHz mono WAV — ideal for Whisper.
    Returns path to the extracted WAV file.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}_audio.wav"

    # Always regenerate audio to avoid stale/corrupted cache issues
    if output_path.exists():
        output_path.unlink()
        logger.info(f"Removed stale audio file: {output_path}")

    cmd = [
        "ffmpeg",
        "-y",                        # overwrite silently
        "-i", str(input_path),
        "-vn",                       # drop video stream
        "-acodec", "pcm_s16le",      # 16-bit PCM
        "-ar", "16000",              # 16kHz sample rate
        "-ac", "1",                  # mono channel
        "-af", "loudnorm",           # normalize loudness
        str(output_path),
    ]

    logger.info(f"Extracting audio: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg audio extraction failed:\n{result.stderr[-1000:]}"
        )

    logger.info(
        f"Audio extracted → {output_path} ({output_path.stat().st_size} bytes)"
    )

    logger.info(
        f"Audio duration = {get_media_duration(output_path):.2f} seconds"
    )

    return output_path


def get_media_duration(input_path: Path) -> float:
    """Return duration in seconds using ffprobe."""

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    try:
        return float(result.stdout.strip())
    except (ValueError, TypeError):
        return 0.0