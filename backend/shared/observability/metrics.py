"""Métricas Prometheus (ADR-015).

- Contadores de negócio contam **depois do commit** (`count_after_commit`): uma operação desfeita
  não pode aparecer no painel como feita.
- Indicadores que já estão no banco (fila do outbox, e-mails pendentes) são lidos **na hora da
  coleta** (`register_gauges`): nada de contador paralelo que pode divergir da fonte da verdade.
- Nomes: `orderflow_<módulo>_<coisa>_<unidade>`; rótulos de baixa cardinalidade (status, código),
  nunca ids.
"""

import contextlib
import os
from collections.abc import Callable, Iterable

import structlog
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    generate_latest,
    multiprocess,
)
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

logger = structlog.get_logger(__name__)

API_ERRORS = Counter(
    "orderflow_api_errors_total",
    "Respostas de erro da API por código do envelope (INSUFFICIENT_STOCK, VALIDATION_ERROR...)",
    ["code", "status"],
)


def count_after_commit(counter: Counter, amount: float = 1, **labels: str) -> None:
    """Incrementa quando (e se) a transação atual confirmar; fora de transação, na hora."""
    transaction.on_commit(lambda: counter.labels(**labels).inc(amount))


GaugeSample = tuple[dict[str, str], float]

_callback_collectors: list["_CallbackCollector"] = []


class _CallbackCollector(Collector):
    def __init__(
        self,
        name: str,
        documentation: str,
        labels: list[str],
        read: Callable[[], Iterable[GaugeSample]],
    ) -> None:
        self.name, self.documentation, self.labels, self.read = name, documentation, labels, read

    def collect(self) -> Iterable[GaugeMetricFamily]:
        family = GaugeMetricFamily(self.name, self.documentation, labels=self.labels)
        try:
            for labels, value in self.read():
                family.add_metric([labels[name] for name in self.labels], value)
        except Exception as exc:  # coleta nunca derruba o /metrics
            logger.warning("metrics.collect.failed", metric=self.name, error=type(exc).__name__)
            return
        yield family

    def describe(self) -> Iterable[GaugeMetricFamily]:
        # Sem `describe`, o registry chamaria `collect` (e o banco) ao registrar.
        return [GaugeMetricFamily(self.name, self.documentation, labels=self.labels)]


def register_gauges(
    name: str, documentation: str, labels: list[str], read: Callable[[], Iterable[GaugeSample]]
) -> None:
    """Gauge calculado a cada coleta. Chamado no `ready()` do app dono do dado."""
    collector = _CallbackCollector(name, documentation, labels, read)
    with contextlib.suppress(ValueError):  # `ready()` de novo (autoreload): já registrado
        REGISTRY.register(collector)
        _callback_collectors.append(collector)


def _registry() -> CollectorRegistry:
    """Um processo: o registry padrão. Vários (gunicorn em produção): a soma dos arquivos de
    `PROMETHEUS_MULTIPROC_DIR` **mais** os gauges lidos do banco — que não passam pelos arquivos
    e sumiriam do `/metrics` se só o coletor multiprocesso fosse usado."""
    if not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return REGISTRY
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
    for collector in _callback_collectors:
        registry.register(collector)
    return registry


def metrics_view(request: HttpRequest) -> HttpResponse:
    """`/metrics` para o Prometheus. Com `METRICS_TOKEN`, exige `Authorization: Bearer <token>`:
    em produção, além de ficar fora da rede pública."""
    token = settings.METRICS_TOKEN
    if token and request.headers.get("Authorization") != f"Bearer {token}":
        return HttpResponse(status=401)
    return HttpResponse(generate_latest(_registry()), content_type=CONTENT_TYPE_LATEST)
