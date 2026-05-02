from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Secure K8s Backend"
    debug: bool = False

    trivy_bin: str = "trivy"
    copa_bin: str = "copa"

    copa_buildkit_addr: str = ""

    reports_dir: Path = Path("/tmp/secure-k8s/reports")
    process_timeout: int = 600


settings = Settings()
settings.reports_dir.mkdir(parents=True, exist_ok=True)
