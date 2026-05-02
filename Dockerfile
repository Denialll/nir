# ── Stage 1: сборка зависимостей ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: финальный образ ──────────────────────────────────────────────────
FROM python:3.11-slim

# Системные утилиты + docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
        https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Trivy через официальный apt-репозиторий
RUN apt-get update && apt-get install -y --no-install-recommends wget apt-transport-https gnupg \
    && wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key \
        | gpg --dearmor > /usr/share/keyrings/trivy.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" \
        > /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends trivy \
    && rm -rf /var/lib/apt/lists/*

# Copacetic
ARG COPA_VERSION=0.10.0
RUN ARCH=$(dpkg --print-architecture) \
    && curl -fsSL \
        "https://github.com/project-copacetic/copacetic/releases/download/v${COPA_VERSION}/copa_${COPA_VERSION}_linux_${ARCH}.tar.gz" \
        | tar xz -C /usr/local/bin copa \
    && chmod +x /usr/local/bin/copa

# Python-пакеты из builder-стадии
COPY --from=builder /install /usr/local

WORKDIR /app
COPY app/ ./app/

# Создаём пользователя и добавляем в группу docker для доступа к socket
RUN useradd --create-home --shell /bin/false appuser \
    && groupadd -f docker \
    && usermod -aG docker appuser \
    && mkdir -p /tmp/secure-k8s/reports \
    && mkdir -p /home/appuser/.cache \
    && chown -R appuser:appuser /app /tmp/secure-k8s /home/appuser

# USER appuser  # запуск от root для доступа к docker.sock

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
