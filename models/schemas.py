from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Subtitle segment ──────────────────────────────────────────────────────────

class SubtitleSegment(BaseModel):
    index: int
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str


# ── Re-segmentation ───────────────────────────────────────────────────────────

class WordsPerSubtitle(str, Enum):
    auto = "auto"
    three = "3"
    four = "4"
    five = "5"
    six = "6"


class ResegmentRequest(BaseModel):
    job_id: str
    segments: list[SubtitleSegment]
    words_per_subtitle: WordsPerSubtitle = WordsPerSubtitle.four


class ResegmentResponse(BaseModel):
    job_id: str
    segments: list[SubtitleSegment]
    original_count: int
    new_count: int
    words_per_subtitle: str


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    job_id: str
    filename: str
    size_bytes: int
    duration_seconds: Optional[float] = None
    message: str


# ── Transcribe ────────────────────────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    job_id: str
    language: str = "hi"           # Whisper language hint — "hi" handles Hinglish well
    task: str = "transcribe"       # "transcribe" | "translate"


class TranscribeResponse(BaseModel):
    job_id: str
    segments: list[SubtitleSegment]
    detected_language: str
    duration_seconds: float
    word_count: int


# ── Subtitle style ────────────────────────────────────────────────────────────

class SubtitleStyle(str, Enum):
    clean_reel = "clean_reel"
    gaming = "gaming"
    meme = "meme"


class StyleOptions(BaseModel):
    style: SubtitleStyle = SubtitleStyle.clean_reel
    font_size: int = Field(22, ge=12, le=48)
    position: str = "bottom"          # "bottom" | "top" | "middle"
    color: str = "&H00FFFFFF"         # ASS color format (AABBGGRR)
    shadow: str = "strong"            # "strong" | "soft" | "none"
    background: str = "none"          # "none" | "semi-dark" | "box"


# ── Export ────────────────────────────────────────────────────────────────────

class ExportFormat(str, Enum):
    srt = "srt"
    ass = "ass"
    mp4 = "mp4"
    all = "all"


class ExportRequest(BaseModel):
    job_id: str
    segments: list[SubtitleSegment]
    format: ExportFormat = ExportFormat.srt
    style: StyleOptions = StyleOptions()
    video_quality: str = "1080p"           # "720p" | "1080p" | "4k"
    words_per_subtitle: str = "4"          # "auto" | "3" | "4" | "5" | "6"
    apply_resegment: bool = True           # run re-segmentation before export


class ExportResponse(BaseModel):
    job_id: str
    format: ExportFormat
    download_url: str
    file_size_bytes: Optional[int] = None
    segment_count: int = 0
    message: str


# ── Job status (for polling) ──────────────────────────────────────────────────

class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = Field(0, ge=0, le=100)
    message: str = ""
    error: Optional[str] = None
