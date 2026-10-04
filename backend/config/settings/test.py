"""Settings para a suíte de testes.

Banco é sempre PostgreSQL (ADR-004); as demais dependências externas são substituídas por
implementações em memória para que os testes não dependam de Redis/RabbitMQ.
"""

import os

# Importado primeiro para que o `.env` local (se existir) seja lido antes dos defaults abaixo.
from .environment import env  # noqa: F401  (efeito colateral: leitura do .env)

# Valores padrão para que `pytest`, `mypy` e `manage.py check` funcionem sem `.env`
# (ex.: na CI, onde DATABASE_URL vem do workflow).
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-insecure-secret-key")
os.environ.setdefault("DATABASE_URL", "postgres://orderflow:orderflow@localhost:5432/orderflow")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")

from .base import *

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Hash de senha rápido: os testes não validam a força do algoritmo.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CELERY_BROKER_URL = "memory://"
