"""Celery: correlação nos logs, métricas por task e endpoint de métricas do worker (ADR-015).

- `correlation_id` vai no header `orderflow_correlation_id` da mensagem (`before_task_publish`) e
  volta para o contexto dos logs no worker (`task_prerun`): o log da task mostra de que requisição
  ela veio. Não pode ser `correlation_id`: é propriedade AMQP que o Celery preenche com o id da
  própria task (achado no E2E — os logs mostravam o id da task, não o da requisição).
- Métricas do worker: processos filhos (prefork) escrevem em `PROMETHEUS_MULTIPROC_DIR`; o
  processo principal serve a soma numa porta própria (`WORKER_METRICS_PORT`).
"""

import os
import time
from typing import Any

import structlog
from celery import signals
from prometheus_client import Counter, Histogram

from shared.logging import get_correlation_id

HEADER = "orderflow_correlation_id"

TASKS = Counter(
    "orderflow_celery_tasks_total", "Tasks executadas por resultado", ["task", "outcome"]
)
TASK_SECONDS = Histogram(
    "orderflow_celery_task_duration_seconds",
    "Duração das tasks",
    ["task"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
_started: dict[str, float] = {}


@signals.before_task_publish.connect
def _propagate_correlation(headers: dict[str, Any] | None = None, **_: Any) -> None:
    correlation_id = get_correlation_id()
    if headers is not None and correlation_id:
        headers.setdefault(HEADER, correlation_id)


@signals.task_prerun.connect
def _bind_task_context(task_id: str = "", task: Any = None, **_: Any) -> None:
    structlog.contextvars.clear_contextvars()
    request = getattr(task, "request", None)
    correlation_id = getattr(request, HEADER, None) or task_id
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id, task_id=task_id, task_name=getattr(task, "name", "")
    )
    _started[task_id] = time.perf_counter()


@signals.task_postrun.connect
def _task_done(task_id: str = "", task: Any = None, state: str = "", **_: Any) -> None:
    name = getattr(task, "name", "unknown")
    started = _started.pop(task_id, None)
    if started is not None:
        TASK_SECONDS.labels(task=name).observe(time.perf_counter() - started)
    if state in ("SUCCESS", "FAILURE"):
        TASKS.labels(task=name, outcome="succeeded" if state == "SUCCESS" else "failed").inc()
    structlog.contextvars.clear_contextvars()


@signals.task_retry.connect
def _task_retried(sender: Any = None, **_: Any) -> None:
    TASKS.labels(task=getattr(sender, "name", "unknown"), outcome="retried").inc()


@signals.worker_process_init.connect
def _init_child(**_: Any) -> None:
    # Depois do fork: cada processo filho tem o próprio exportador de traces.
    from shared.observability.tracing import configure_tracing

    configure_tracing(os.environ.get("SERVICE_NAME", "orderflow-worker"), web=False)


@signals.worker_ready.connect
def _serve_worker_metrics(**_: Any) -> None:
    port = os.environ.get("WORKER_METRICS_PORT")
    if not port or not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return
    from prometheus_client import CollectorRegistry, multiprocess, start_http_server

    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
    start_http_server(int(port), registry=registry)
    structlog.get_logger(__name__).info("observability.worker_metrics.serving", port=port)


@signals.worker_process_shutdown.connect
def _child_gone(pid: int | None = None, **_: Any) -> None:
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR") and pid:
        from prometheus_client import multiprocess

        multiprocess.mark_process_dead(pid)  # type: ignore[no-untyped-call]
