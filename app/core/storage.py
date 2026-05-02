from __future__ import annotations

from threading import Lock

from app.schemas.scan import ScanReport


class ReportStorage:
    """In-memory хранилище отчётов сканирования.

    На этапе НИР этого хватит. При переходе в продакшн заменяется
    на репозиторий поверх PostgreSQL без изменения вызывающего кода.
    """

    def __init__(self) -> None:
        self._reports: dict[str, ScanReport] = {}
        self._lock = Lock()

    def save(self, report: ScanReport) -> None:
        with self._lock:
            self._reports[report.scan_id] = report

    def get(self, scan_id: str) -> ScanReport | None:
        with self._lock:
            return self._reports.get(scan_id)

    def list_all(self) -> list[ScanReport]:
        with self._lock:
            return list(self._reports.values())


storage = ReportStorage()
