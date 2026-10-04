# syntax=docker/dockerfile:1
# Imagem do backend (Django + Celery). Contexto de build: raiz do repositório.

FROM ghcr.io/astral-sh/uv:0.12.23 AS uv

FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH"
COPY --from=uv /uv /uvx /usr/local/bin/
RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app

# Desenvolvimento: dependências (incluindo dev) na imagem, código montado como volume.
FROM base AS dev
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked
USER app
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Produção: somente dependências de runtime e o código; servidor WSGI gunicorn.
FROM base AS production
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --locked --no-dev
COPY backend/ ./
USER app
EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=config.settings.production
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
