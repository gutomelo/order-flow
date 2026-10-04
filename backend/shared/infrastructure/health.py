"""Health checks (docs/architecture/observability.md).

- `/health/live`: o processo responde. Sem dependências, para não reiniciar o container por
  causa de uma falha de banco/broker que reiniciar não resolve.
- `/health/ready`: as dependências necessárias para atender tráfego estão acessíveis.

Respostas nunca incluem mensagens de erro das dependências (podem conter hosts e credenciais);
o tipo do erro vai apenas para o log.
"""

from collections.abc import Callable

import structlog
from celery import current_app as celery_app
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

logger = structlog.get_logger(__name__)

OK = "ok"
UNAVAILABLE = "unavailable"


def check_database() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def check_cache() -> None:
    cache.set("health:ping", "pong", timeout=5)
    if cache.get("health:ping") != "pong":
        raise RuntimeError("cache round-trip failed")


def check_broker() -> None:
    with celery_app.connection_for_read() as conn:
        conn.ensure_connection(max_retries=1, timeout=3)


READINESS_CHECKS: dict[str, Callable[[], None]] = {
    "database": check_database,
    "cache": check_cache,
    "broker": check_broker,
}


@require_GET
def live(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": OK})


@require_GET
def ready(request: HttpRequest) -> JsonResponse:
    results: dict[str, str] = {}
    for name, check in READINESS_CHECKS.items():
        try:
            check()
            results[name] = OK
        except Exception as exc:
            logger.warning("health.check.failed", check=name, error_type=type(exc).__name__)
            results[name] = UNAVAILABLE

    healthy = all(result == OK for result in results.values())
    return JsonResponse(
        {"status": OK if healthy else UNAVAILABLE, "checks": results},
        status=200 if healthy else 503,
    )
