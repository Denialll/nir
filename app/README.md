# Secure K8s Backend

Бэкенд программного комплекса безопасной разработки контейнерных приложений.

## Стек

- FastAPI (Python 3.11+)
- Trivy (сканирование уязвимостей)
- Copacetic / `copa` (патчинг образов)

## Требования к среде

- Python 3.11+
- Установленный `trivy` в PATH (или указать путь в `TRIVY_BIN`)
- Установленный `copa` в PATH (или указать путь в `COPA_BIN`)
- Docker + buildkit для работы Copacetic

## Запуск

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: http://localhost:8000/docs

## Эндпоинты

- `POST /scan` — сканирование образа
- `GET /scan/{scan_id}` — получить отчёт
- `GET /scan` — список отчётов
- `POST /patch` — патчинг по `scan_id`
- `GET /health` — healthcheck

## Пример

```bash
# 1. Сканируем
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"image": "nginx:1.21", "severity": ["CRITICAL", "HIGH"], "ignore_unfixed": true}'

# 2. Берём scan_id из ответа и патчим
curl -X POST http://localhost:8000/patch \
  -H "Content-Type: application/json" \
  -d '{"scan_id": "<scan_id>"}'
```

## Структура

```
app/
├── api/         # роутеры FastAPI
├── core/        # конфиг, хранилище
├── schemas/     # pydantic-модели
├── services/    # обёртки над trivy и copa
└── main.py
```
