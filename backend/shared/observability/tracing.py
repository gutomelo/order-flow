"""Tracing OpenTelemetry (ADR-015). Desligado sem `OTEL_EXPORTER_OTLP_ENDPOINT`.

Instrumenta Django (requisições), psycopg (consultas), Redis e Celery. O contexto do trace também
atravessa o outbox (`DomainEvent.trace_context` → `shared.events.bus.deliver`): a requisição, a
entrega do evento e o e-mail que ela gera ficam no mesmo trace.
"""

import os

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)

# Estado do processo (configurar duas vezes duplicaria spans e instrumentação).
_state = {"configured": False}

# Rotas sem valor diagnóstico (e de alto volume) ficam fora dos traces.
EXCLUDED_URLS = "health/live,health/ready,metrics"


def configure_tracing(service_name: str, *, web: bool) -> bool:
    """Liga o tracing do processo. `web=True` instrumenta o Django (antes de carregar os
    middlewares); o worker chama no `worker_process_init` (depois do fork)."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
    if _state["configured"] or not endpoint:
        return False
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "deployment.environment": os.environ.get("ENVIRONMENT", "local"),
            }
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(provider)

    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    if web:
        from opentelemetry.instrumentation.django import DjangoInstrumentor

        DjangoInstrumentor().instrument(excluded_urls=EXCLUDED_URLS)
    PsycopgInstrumentor().instrument()
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()  # type: ignore[no-untyped-call]  # pacote sem tipos
    _state["configured"] = True
    logger.info("observability.tracing.enabled", service=service_name)
    return True
