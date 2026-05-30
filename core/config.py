from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    whisper_model: str = "large-v3"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"

    max_upload_size_mb: int = 500
    temp_file_ttl_hours: int = 2
    temp_dir: Path = Path("./temp")

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def uploads_dir(self) -> Path:
        return self.temp_dir / "uploads"

    @property
    def audio_dir(self) -> Path:
        return self.temp_dir / "audio"

    @property
    def outputs_dir(self) -> Path:
        return self.temp_dir / "outputs"


settings = Settings()
