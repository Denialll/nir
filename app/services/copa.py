from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.schemas.scan import PatchResult, RegistryCredentials, ScanReport
from app.services.registry import RegistryError, registry_service


class CopaError(RuntimeError):
    """Ошибка выполнения Copacetic."""


class CopaService:
    """Обёртка над `copa patch`.

    Copa патчит ОС-пакеты образа. После патча — опциональный пуш в registry.
    """

    def __init__(self, binary: str = settings.copa_bin) -> None:
        self._binary = binary

    async def patch(
        self,
        report: ScanReport,
        output_tag: str | None = None,
        registry_creds: RegistryCredentials | None = None,
    ) -> PatchResult:
        report_path = Path(report.raw_report_path)
        if not report_path.exists():
            raise CopaError(f"Отчёт сканирования не найден: {report_path}")

        patched_image = output_tag or self._derive_patched_tag(report.image)

        copa_timeout_min = max(1, settings.process_timeout // 60)
        cmd = [
            self._binary,
            "patch",
            "--image", report.image,
            "--report", str(report_path),
            "--tag", self._tag_only(patched_image),
            "--timeout", f"{copa_timeout_min}m",
        ]
        if settings.copa_buildkit_addr:
            cmd += ["--addr", settings.copa_buildkit_addr]

        log = await self._run(cmd)

        # Пуш в registry — только если пользователь передал credentials
        pushed_image: str | None = None
        if registry_creds is not None:
            pushed_image = await registry_service.push(patched_image, registry_creds)

        return PatchResult(
            scan_id=report.scan_id,
            original_image=report.image,
            patched_image=patched_image,
            pushed_image=pushed_image,
            patched_at=datetime.now(timezone.utc),
            copa_log=log,
        )

    async def _run(self, cmd: list[str]) -> str:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=settings.process_timeout
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise CopaError(f"Copa timeout после {settings.process_timeout}s") from exc

        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        if process.returncode != 0:
            raise CopaError(f"Copa завершился с кодом {process.returncode}: {err.strip() or out.strip()}")

        return (out + err).strip()

    @staticmethod
    def _derive_patched_tag(image: str) -> str:
        if ":" in image.rsplit("/", 1)[-1]:
            return f"{image}-patched"
        return f"{image}:patched"

    @staticmethod
    def _tag_only(full_image: str) -> str:
        _, _, tag = full_image.rpartition(":")
        return tag or "patched"


copa_service = CopaService()