from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    image: str = Field(..., examples=["nginx:1.21"])
    severity: list[str] = Field(default_factory=lambda: ["CRITICAL", "HIGH"])
    ignore_unfixed: bool = Field(default=False)


class Vulnerability(BaseModel):
    vulnerability_id: str
    pkg_name: str
    installed_version: str
    fixed_version: str | None = None
    severity: str
    title: str | None = None
    primary_url: str | None = None


class ScanReport(BaseModel):
    scan_id: str
    image: str
    scanned_at: datetime
    total_vulnerabilities: int
    by_severity: dict[str, int]
    vulnerabilities: list[Vulnerability]
    raw_report_path: str


class RegistryCredentials(BaseModel):
    """Параметры registry для пуша пропатченного образа.

    Передаются в теле запроса POST /patch.
    Поддерживается любой Docker-совместимый registry: Harbor, Docker Hub, GHCR, ECR и т.д.
    """

    url: str = Field(
        ...,
        description="Адрес registry без схемы",
        examples=["harbor.example.com", "ghcr.io", "registry.example.com:5000"],
    )
    project: str = Field(
        ...,
        description="Проект / namespace внутри registry",
        examples=["myproject", "myorg/myteam"],
    )
    username: str = Field(..., examples=["robot$myrobot", "myuser"])
    password: str = Field(..., description="Пароль или токен. Не возвращается в ответе.")


class PatchRequest(BaseModel):
    scan_id: str
    output_tag: str | None = Field(
        default=None,
        description="Тег пропатченного образа. По умолчанию '<original>-patched'",
    )
    registry: RegistryCredentials | None = Field(
        default=None,
        description="Если передан — пропатченный образ будет запушен в указанный registry",
    )


class PatchResult(BaseModel):
    scan_id: str
    original_image: str
    patched_image: str
    pushed_image: str | None = Field(
        default=None,
        description="Полный тег в registry, если пуш был выполнен",
    )
    patched_at: datetime
    copa_log: str | None = None