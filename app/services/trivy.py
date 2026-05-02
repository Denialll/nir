from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.schemas.scan import ScanReport, ScanRequest, Vulnerability

log = logging.getLogger(__name__)


class TrivyError(RuntimeError):
    pass


class TrivyService:
    def __init__(self, binary: str = settings.trivy_bin, reports_dir: Path = settings.reports_dir) -> None:
        self._binary = binary
        self._reports_dir = reports_dir

    async def scan(self, request: ScanRequest) -> ScanReport:
        scan_id = str(uuid.uuid4())
        report_path = self._reports_dir / f"{scan_id}.json"

        log.info("Запуск сканирования | image=%s severity=%s", request.image, request.severity)

        cmd = [
            self._binary, "image",
            "--quiet",
            "--format", "json",
            "--output", str(report_path),
            "--severity", ",".join(request.severity),
            "--scanners", "vuln",
            "--vuln-type", "os,library",
        ]
        if request.ignore_unfixed:
            cmd.append("--ignore-unfixed")
        cmd.append(request.image)

        log.debug("Команда: %s", " ".join(cmd))
        await self._run(cmd)

        if not report_path.exists():
            raise TrivyError(f"Trivy не создал отчёт: {report_path}")

        raw = json.loads(report_path.read_text(encoding="utf-8"))
        vulnerabilities = self._extract_vulnerabilities(raw)

        log.info(
            "Сканирование завершено | scan_id=%s image=%s total=%d",
            scan_id, request.image, len(vulnerabilities),
        )

        return ScanReport(
            scan_id=scan_id,
            image=request.image,
            scanned_at=datetime.now(timezone.utc),
            total_vulnerabilities=len(vulnerabilities),
            by_severity=dict(Counter(v.severity for v in vulnerabilities)),
            vulnerabilities=vulnerabilities,
            raw_report_path=str(report_path),
        )

    async def _run(self, cmd: list[str]) -> None:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=settings.process_timeout)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise TrivyError(f"Trivy timeout после {settings.process_timeout}s") from exc

        if process.returncode != 0:
            err = stderr.decode("utf-8", errors="replace") or stdout.decode("utf-8", errors="replace")
            log.error("Trivy завершился с ошибкой: %s", err.strip())
            raise TrivyError(f"Trivy завершился с кодом {process.returncode}: {err.strip()}")

    @staticmethod
    def _extract_vulnerabilities(raw_report: dict) -> list[Vulnerability]:
        results = raw_report.get("Results") or []
        vulns: list[Vulnerability] = []
        for result in results:
            for v in result.get("Vulnerabilities") or []:
                vulns.append(Vulnerability(
                    vulnerability_id=v.get("VulnerabilityID", "UNKNOWN"),
                    pkg_name=v.get("PkgName", ""),
                    installed_version=v.get("InstalledVersion", ""),
                    fixed_version=v.get("FixedVersion"),
                    severity=v.get("Severity", "UNKNOWN"),
                    title=v.get("Title"),
                    primary_url=v.get("PrimaryURL"),
                ))
        return vulns


trivy_service = TrivyService()