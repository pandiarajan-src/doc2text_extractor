from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    host: str = "0.0.0.0"
    port: int = 8081
    debug: bool = False

    # File handling
    max_file_size_mb: int = 50
    max_workers: int = 4

    # Directories
    uploads_dir: str = "uploads"
    outputs_dir: str = "outputs"

    # Job management
    cleanup_hours: int = 24
    uploads_cleanup_hours: int = 1

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour in seconds

    # CORS
    cors_origins: list = ["*"]

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def uploads_path(self) -> Path:
        return Path(self.uploads_dir).resolve()

    @property
    def outputs_path(self) -> Path:
        return Path(self.outputs_dir).resolve()


settings = Settings()
