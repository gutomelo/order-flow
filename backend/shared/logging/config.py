"""Configuração de logging estruturado (docs/architecture/observability.md).

Logs do structlog e da biblioteca padrão (Django, Celery, bibliotecas) passam pelo mesmo
`ProcessorFormatter`, produzindo uma única saída consistente: JSON em ambientes reais e
console legível em desenvolvimento.
"""

from typing import Any

import structlog
from structlog.typing import Processor

from shared.logging.processors import add_service_name, redact_sensitive_data


def _shared_processors(service: str) -> list[Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_service_name(service),
        redact_sensitive_data,
    ]


def build_logging_config(
    *, level: str, json_output: bool, service: str = "orderflow-api"
) -> dict[str, Any]:
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    final_processors: list[Processor] = [structlog.stdlib.ProcessorFormatter.remove_processors_meta]
    if json_output:
        final_processors.append(structlog.processors.format_exc_info)
    final_processors.append(renderer)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": final_processors,
                "foreign_pre_chain": _shared_processors(service),
            },
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "structured"},
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            # Substitui os handlers padrão do Django (DEFAULT_LOGGING), que duplicariam as
            # mensagens em texto puro fora do formato estruturado.
            "django": {"handlers": ["console"], "level": level, "propagate": False},
            # O RequestIdMiddleware já registra cada requisição com contexto estruturado.
            "django.server": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        },
    }


def configure_structlog(*, service: str, json_output: bool) -> None:
    structlog.configure(
        processors=[
            *_shared_processors(service),
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
