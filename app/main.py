from __future__ import annotations

from fastapi import FastAPI

from app.api import patch, scan
from app.core.config import settings
from app.core.logger import setup_logging

setup_logging(debug=settings.debug)

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Программный комплекс безопасной разработки контейнерных приложений. "
            "Сканирование (Trivy) и автоматический патчинг (Copacetic) образов."
        ),
        version="0.1.0",
        debug=settings.debug,
    )

    app.include_router(scan.router)
    app.include_router(patch.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()