"""Gunicorn em produção (ADR-015): métricas de vários processos somadas pelo `/metrics`.

`PROMETHEUS_MULTIPROC_DIR` aponta para um diretório vazio a cada início (Dockerfile); quando um
worker do gunicorn sai, os arquivos dele deixam de contar nos gauges "ao vivo".
"""

from typing import Any

from prometheus_client import multiprocess


def child_exit(server: Any, worker: Any) -> None:
    multiprocess.mark_process_dead(worker.pid)  # type: ignore[no-untyped-call]
