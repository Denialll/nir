from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.storage import storage
from app.schemas.scan import PatchRequest, PatchResult
from app.services.copa import CopaError, copa_service
from app.services.registry import RegistryError

router = APIRouter(prefix="/patch", tags=["patch"])


@router.post("", response_model=PatchResult, status_code=status.HTTP_200_OK)
async def patch_image(request: PatchRequest) -> PatchResult:
    """Патчинг образа на основе ранее выполненного сканирования.

    Опционально: передай блок `registry` — пропатченный образ будет запушен туда.
    """
    report = storage.get(request.scan_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Отчёт сканирования {request.scan_id} не найден. Сначала выполните /scan.",
        )

    if report.total_vulnerabilities == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В отчёте нет уязвимостей — патчить нечего.",
        )

    try:
        result = await copa_service.patch(
            report,
            output_tag=request.output_tag,
            registry_creds=request.registry,
        )
    except CopaError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except RegistryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Патч выполнен, но пуш в registry упал: {exc}",
        ) from exc

    return result