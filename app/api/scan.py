from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.storage import storage
from app.schemas.scan import ScanReport, ScanRequest
from app.services.trivy import TrivyError, trivy_service

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanReport, status_code=status.HTTP_200_OK)
async def scan_image(request: ScanRequest) -> ScanReport:
    """Запуск сканирования образа через Trivy."""
    try:
        report = await trivy_service.scan(request)
    except TrivyError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    storage.save(report)
    return report


@router.get("/{scan_id}", response_model=ScanReport)
async def get_scan_report(scan_id: str) -> ScanReport:
    """Получение ранее выполненного отчёта."""
    report = storage.get(scan_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отчёт не найден")
    return report


@router.get("", response_model=list[ScanReport])
async def list_scans() -> list[ScanReport]:
    """Список всех отчётов."""
    return storage.list_all()
