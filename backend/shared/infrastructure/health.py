"""Health checks (docs/architecture/observability.md).

- `/health/live`: o processo responde. Sem dependências, para não reiniciar o container por
  causa de uma falha de banco/broker que reiniciar não resolve.
- `/health/ready`: as dependências necessárias para atender tráfego estão acessíveis.

Respostas nunca incluem mensagens de erro das dependências (podem conter hosts e credenciais);
o tipo do erro vai apenas para o log.
"""

import base64
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

import structlog
from celery import current_app as celery_app
from django.conf import settings
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


class BrokerAlarm(RuntimeError):
    """RabbitMQ com alarme (disco ou memória): aceita conexão, mas bloqueia publicações."""


def check_broker() -> None:
    with celery_app.connection_for_read() as conn:
        conn.ensure_connection(max_retries=1, timeout=3)
    _check_broker_alarms()


def _check_broker_alarms() -> None:
    """Conectar não basta: com alarme o RabbitMQ aceita a conexão e só bloqueia quem publica
    (visto na Phase 10 com o disco cheio — a prontidão dizia "ok" e nada andava). A API de
    gerenciamento responde 503 quando há alarme."""
    url = settings.RABBITMQ_MANAGEMENT_URL
    if not url:
        return
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("RABBITMQ_MANAGEMENT_URL deve ser http(s)")
    request = urllib.request.Request(  # noqa: S310 (esquema validado acima)
        f"{parts.scheme}://{parts.hostname}:{parts.port or 15672}/api/health/checks/alarms"
    )
    if parts.username:
        credentials = f"{parts.username}:{parts.password or ''}".encode()
        request.add_header("Authorization", f"Basic {base64.b64encode(credentials).decode()}")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:  # noqa: S310 (idem)
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        if exc.code == 503:
            raise BrokerAlarm() from None
        raise
    if body.get("status") != "ok":
        raise BrokerAlarm()


READINESS_CHECKS: dict[str, Callable[[], None]] = {
    "database": check_database,
    "cache": check_cache,
    "broker": check_broker,
}


def run_checks() -> dict[str, str]:
    results: dict[str, str] = {}
    for name, check in READINESS_CHECKS.items():
        try:
            check()
            results[name] = OK
        except Exception as exc:
            logger.warning("health.check.failed", check=name, error_type=type(exc).__name__)
            results[name] = UNAVAILABLE
    return results


def dependency_gauges() -> Iterable[tuple[dict[str, str], float]]:
    """`orderflow_dependency_up{dependency}` (1/0) a cada coleta do Prometheus."""
    for name, result in run_checks().items():
        yield {"dependency": name}, 1.0 if result == OK else 0.0


@require_GET
def live(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": OK})


@require_GET
def ready(request: HttpRequest) -> JsonResponse:
    results = run_checks()
    healthy = all(result == OK for result in results.values())
    return JsonResponse(
        {"status": OK if healthy else UNAVAILABLE, "checks": results},
        status=200 if healthy else 503,
    )
