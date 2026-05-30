"""
Export service.

Generates SRT, ASS, and optionally burns subtitles into MP4.
Re-segmentation is handled upstream (in the route) before this is called.
"""
import subprocess
import zipfile
import logging
from pathlib import Path
from typing import Optional

from models.schemas import ExportFormat, StyleOptions, SubtitleSegment
from services.subtitle_service import segments_to_srt, segments_to_ass

logger = logging.getLogger(__name__)


QUALITY_PRESETS: dict[str, dict] = {
    "720p":  {"scale": "1280:720",   "vbitrate": "3000k",  "abitrate": "128k"},
    "1080p": {"scale": "1920:1080",  "vbitrate": "6000k",  "abitrate": "192k"},
    "4k":    {"scale": "3840:2160",  "vbitrate": "20000k", "abitrate": "256k"},
}


def burn_subtitles(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
    quality: str = "1080p",
) -> Path:
    """Burn ASS subtitles onto video via FFmpeg libass. Returns output path."""
    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["1080p"])
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"scale={preset['scale']},ass={ass_escaped}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-b:v", preset["vbitrate"],
        "-c:a", "aac",
        "-b:a", preset["abitrate"],
        "-movflags", "+faststart",
        str(output_path),
    ]

    logger.info(f"Burning subtitles → {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg subtitle burn failed:\n{result.stderr[-2000:]}")

    logger.info(f"Burn complete — {output_path.stat().st_size} bytes")
    return output_path


def export(
    job_id: str,
    segments: list[SubtitleSegment],
    style_options: StyleOptions,
    export_format: ExportFormat,
    output_dir: Path,
    video_path: Optional[Path] = None,
    quality: str = "1080p",
) -> Path:
    """
    Main export entry point. Segments should already be re-segmented
    by the caller before this function is invoked.

    Returns path to the primary output file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / job_id

    srt_path = base.with_suffix(".srt")
    ass_path = base.with_suffix(".ass")
    mp4_path = base.with_suffix(".mp4")
    zip_path = base.with_suffix(".zip")

    # SRT is always generated (fast, and needed for ZIP)
    segments_to_srt(segments, srt_path)

    if export_format == ExportFormat.srt:
        logger.info(f"SRT export ready — {len(segments)} segments")
        return srt_path

    # ASS needed for styled exports and MP4 burn
    segments_to_ass(segments, style_options, ass_path)

    if export_format == ExportFormat.ass:
        return ass_path

    if export_format == ExportFormat.mp4:
        if not video_path:
            raise RuntimeError("video_path is required for MP4 export")
        return burn_subtitles(video_path, ass_path, mp4_path, quality)

    if export_format == ExportFormat.all:
        if not video_path:
            raise RuntimeError("video_path is required for 'all' export")
        burn_subtitles(video_path, ass_path, mp4_path, quality)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(mp4_path, mp4_path.name)
            zf.write(srt_path,  srt_path.name)
            zf.write(ass_path,  ass_path.name)
        logger.info(f"ZIP created — {zip_path.stat().st_size} bytes")
        return zip_path

    raise ValueError(f"Unknown export format: {export_format}")
