"""
Subtitle generation service.

Converts timed segments + style options into:
  - .srt  (SubRip — universal)
  - .ass  (Advanced SubStation Alpha — styled)

Uses pysubs2 for all file format handling.
"""
import logging
from pathlib import Path

import pysubs2

from models.schemas import SubtitleSegment, StyleOptions, SubtitleStyle

logger = logging.getLogger(__name__)


# ── ASS style presets ─────────────────────────────────────────────────────────

def _build_ass_style(options: StyleOptions) -> pysubs2.SSAStyle:
    """Build a pysubs2 SSAStyle from our StyleOptions model."""
    style = pysubs2.SSAStyle()

    if options.style == SubtitleStyle.clean_reel:
        style.fontname = "Arial"
        style.fontsize = options.font_size
        style.bold = True
        style.primarycolor = pysubs2.Color(255, 255, 255, 0)   # white
        style.outlinecolor = pysubs2.Color(0, 0, 0, 0)          # black outline
        style.backcolor = pysubs2.Color(0, 0, 0, 128)           # semi-transparent shadow
        style.outline = 2.5
        style.shadow = 2.0
        style.alignment = pysubs2.Alignment.BOTTOM_CENTER
        style.marginv = 30

    elif options.style == SubtitleStyle.gaming:
        style.fontname = "Impact"
        style.fontsize = options.font_size + 2
        style.bold = True
        style.primarycolor = pysubs2.Color(0, 255, 136, 0)     # neon green
        style.outlinecolor = pysubs2.Color(0, 0, 0, 0)
        style.backcolor = pysubs2.Color(0, 0, 0, 180)
        style.outline = 3.0
        style.shadow = 0.0
        style.alignment = pysubs2.Alignment.BOTTOM_CENTER
        style.marginv = 25
        style.uppercase = True

    elif options.style == SubtitleStyle.meme:
        style.fontname = "Impact"
        style.fontsize = options.font_size + 6
        style.bold = True
        style.primarycolor = pysubs2.Color(249, 115, 22, 0)    # orange
        style.outlinecolor = pysubs2.Color(0, 0, 0, 0)
        style.backcolor = pysubs2.Color(0, 0, 0, 0)
        style.outline = 4.0
        style.shadow = 0.0
        style.alignment = pysubs2.Alignment.BOTTOM_CENTER
        style.marginv = 20

    # Override position
    if options.position == "top":
        style.alignment = pysubs2.Alignment.TOP_CENTER
        style.marginv = 20
    elif options.position == "middle":
        style.alignment = pysubs2.Alignment.MIDDLE_CENTER

    # Box background
    if options.background == "box":
        style.borderstyle = 3          # opaque box
        style.backcolor = pysubs2.Color(0, 0, 0, 80)

    return style


def _seconds_to_ms(seconds: float) -> int:
    return int(seconds * 1000)


def segments_to_srt(segments: list[SubtitleSegment], output_path: Path) -> Path:
    """Write segments to a .srt file."""
    subs = pysubs2.SSAFile()

    for seg in segments:
        event = pysubs2.SSAEvent(
            start=_seconds_to_ms(seg.start),
            end=_seconds_to_ms(seg.end),
            text=seg.text,
        )
        subs.append(event)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(output_path), format_="srt")
    logger.info(f"SRT saved → {output_path}")
    return output_path


def segments_to_ass(
    segments: list[SubtitleSegment],
    style_options: StyleOptions,
    output_path: Path,
) -> Path:
    """Write segments to a styled .ass file."""
    subs = pysubs2.SSAFile()

    # Build and apply style
    ass_style = _build_ass_style(style_options)
    subs.styles["Default"] = ass_style

    for seg in segments:
        text = seg.text
        # Apply uppercase transformation at text level for gaming style
        if style_options.style == SubtitleStyle.gaming:
            text = text.upper()

        event = pysubs2.SSAEvent(
            start=_seconds_to_ms(seg.start),
            end=_seconds_to_ms(seg.end),
            text=text,
            style="Default",
        )
        subs.append(event)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subs.save(str(output_path), format_="ass")
    logger.info(f"ASS saved → {output_path}")
    return output_path
