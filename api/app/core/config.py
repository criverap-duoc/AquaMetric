"""Runtime configuration read from environment variables and api/.env."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Final, Literal

from fastapi import Depends
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# api/app/core/config.py -> repository root, so the shared catalog resolves from any cwd.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Page-size ceiling of `GET /observations`, kept as a constant because it bounds a Query
# parameter at import time. The Series screen reads up to 500 rows in one request (30 days of a
# six-hourly series) and the control chart asks for its whole Phase I window; 1000 covers both.
OBSERVATIONS_PAGE_SIZE_MAX: Final = 1000


class Settings(BaseSettings):
    """Validated settings; no secret has a default so a misconfigured deploy fails at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["local", "ci", "staging", "production"] = "local"
    database_url: str = "postgresql+asyncpg://aquametric:aquametric@localhost:5433/aquametric"
    ingest_api_key: str = Field(min_length=16)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5174"]
    catalog_dir: Path = REPO_ROOT / "catalog"
    aws_region: str = "us-east-1"
    s3_bucket: str | None = None
    # ADR-004: the live demo feeds the API directly, so the S3 → Lambda pipeline is optional and
    # the pipeline screen must be able to say so instead of pretending the objects exist.
    aws_pipeline_deployed: bool = False
    baseline_min_points: int = Field(default=20, ge=2)
    censored_max_fraction: float = Field(default=0.2, ge=0.0, lt=1.0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Accept `a,b` in .env; Pydantic would otherwise demand a JSON array."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cache settings so every request and startup hook sees the same validated values."""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
