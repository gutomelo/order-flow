"""Observabilidade (Phase 13, ADR-015): métricas, correlação ponta a ponta e tracing."""

import urllib.error
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
import structlog
from django.db import transaction
from django.test import Client, override_settings
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from prometheus_client import REGISTRY

from apps.identity.domain.permissions import Role
from apps.orders.tests.factories import ORDERS, make_scenario
from shared.events.base import DomainEvent, EventEnvelope
from shared.events.bus import deliver, publish, subscribe
from shared.events.models import OutboxEvent
from shared.logging import get_correlation_id
from shared.logging.processors import add_trace_ids
from shared.observability import celery as celery_signals
from shared.observability.tracing import configure_tracing

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _value(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


# Métricas --------------------------------------------------------------------------------------


def test_business_counters_count_only_what_was_committed(
    django_capture_on_commit_callbacks: Any,
) -> None:
    s = make_scenario(role=Role.MANAGER)
    s.stock(s.cola, 10)
    s.stock(s.water, 10)
    before = _value("orderflow_order_transitions_total", to_status="AWAITING_PAYMENT")

    with django_capture_on_commit_callbacks(execute=False):
        s.place()  # transação "desfeita": os callbacks de commit não rodam
    rolled_back = _value("orderflow_order_transitions_total", to_status="AWAITING_PAYMENT")
    with django_capture_on_commit_callbacks(execute=True):
        s.place()

    assert rolled_back == before
    assert _value("orderflow_order_transitions_total", to_status="AWAITING_PAYMENT") == before + 1


def test_api_errors_are_counted_by_envelope_code() -> None:
    s = make_scenario()
    before = _value("orderflow_api_errors_total", code="NOT_FOUND", status="404")

    s.client.get(f"{ORDERS}/{uuid4()}")

    assert _value("orderflow_api_errors_total", code="NOT_FOUND", status="404") == before + 1


def test_metrics_endpoint_exposes_http_database_and_outbox_metrics() -> None:
    with transaction.atomic():
        publish(Pinged())

    body = Client().get("/metrics").content.decode()

    assert "django_http_requests_latency_seconds_by_view_method" in body
    assert "django_db_execute_total" in body
    assert 'orderflow_outbox_pending{measure="count"} 1.0' in body
    assert 'orderflow_outbox_pending{measure="oldest_age_seconds"}' in body


@override_settings(METRICS_TOKEN="segredo-de-teste")
def test_metrics_require_the_token_when_configured() -> None:
    assert Client().get("/metrics").status_code == 401
    authorized = Client().get("/metrics", HTTP_AUTHORIZATION="Bearer segredo-de-teste")
    assert authorized.status_code == 200


@override_settings(RABBITMQ_MANAGEMENT_URL="http://guest:guest@rabbitmq:15672")
def test_a_broker_alarm_makes_the_service_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    def alarm(*args: Any, **kwargs: Any) -> None:
        raise urllib.error.HTTPError("url", 503, "alarms", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr("urllib.request.urlopen", alarm)

    response = Client().get("/health/ready")
    metrics = Client().get("/metrics").content.decode()

    assert response.status_code == 503
    assert response.json()["checks"]["broker"] == "unavailable"
    assert 'orderflow_dependency_up{dependency="broker"} 0.0' in metrics
    assert 'orderflow_dependency_up{dependency="database"} 1.0' in metrics


# Correlação ------------------------------------------------------------------------------------

seen: dict[str, Any] = {}


class Pinged(DomainEvent):
    event_name = "tests.observability.pinged"


@subscribe("tests.observability.pinged")
def remember_context(event: EventEnvelope) -> None:
    seen["correlation_id"] = get_correlation_id()
    seen["span"] = trace.get_current_span().get_span_context()


def test_the_correlation_id_travels_from_the_request_to_the_event_handler() -> None:
    with (
        structlog.contextvars.bound_contextvars(correlation_id="corr-123", request_id="req-1"),
        transaction.atomic(),
    ):
        publish(Pinged())
    event = OutboxEvent.objects.get(event_name="tests.observability.pinged")
    structlog.contextvars.clear_contextvars()  # o worker começa sem contexto

    deliver(str(event.id), "tests.shared.test_observability.remember_context")

    assert event.payload["correlation_id"] == "corr-123"
    assert seen["correlation_id"] == "corr-123"


def test_celery_messages_carry_the_correlation_id_to_the_worker_logs() -> None:
    headers: dict[str, Any] = {}
    with structlog.contextvars.bound_contextvars(correlation_id="corr-xyz"):
        celery_signals._propagate_correlation(headers=headers)

    class Request:
        correlation_id = "id-da-task"  # propriedade AMQP que o Celery preenche: não é a nossa
        orderflow_correlation_id = headers["orderflow_correlation_id"]

    class Task:
        name = "notifications.send"
        request = Request()

    celery_signals._bind_task_context(task_id="t-1", task=Task())
    bound = structlog.contextvars.get_contextvars()
    before = _value("orderflow_celery_tasks_total", task="notifications.send", outcome="succeeded")
    celery_signals._task_done(task_id="t-1", task=Task(), state="SUCCESS")

    assert headers == {"orderflow_correlation_id": "corr-xyz"}
    assert (bound["correlation_id"], bound["task_id"]) == ("corr-xyz", "t-1")
    after = _value("orderflow_celery_tasks_total", task="notifications.send", outcome="succeeded")
    assert after == before + 1
    assert structlog.contextvars.get_contextvars() == {}  # contexto limpo para a próxima task


# Tracing ---------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def spans() -> Iterator[InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)  # uma vez por processo de teste
    yield exporter


def test_tracing_stays_off_without_an_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert configure_tracing("orderflow-test", web=True) is False


def test_the_trace_continues_through_the_outbox(spans: InMemorySpanExporter) -> None:
    tracer = trace.get_tracer("tests")
    with tracer.start_as_current_span("POST /orders") as request_span, transaction.atomic():
        publish(Pinged())
    event = OutboxEvent.objects.filter(event_name="tests.observability.pinged").latest(
        "occurred_at"
    )

    deliver(str(event.id), "tests.shared.test_observability.remember_context")

    delivery = next(s for s in spans.get_finished_spans() if s.name == f"event {Pinged.event_name}")
    origin = request_span.get_span_context()
    assert delivery.context.trace_id == origin.trace_id  # mesmo trace da requisição
    assert delivery.parent is not None and delivery.parent.span_id == origin.span_id
    assert seen["span"].trace_id == origin.trace_id  # o handler roda dentro dele


def test_logs_carry_the_trace_id_when_a_span_is_active(spans: InMemorySpanExporter) -> None:
    with trace.get_tracer("tests").start_as_current_span("x") as span:
        event = add_trace_ids(None, "info", {})

    assert event["trace_id"] == format(span.get_span_context().trace_id, "032x")
    assert add_trace_ids(None, "info", {}) == {}  # sem span ativo, nada


def test_with_several_processes_the_endpoint_still_exposes_the_database_gauges(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Produção (gunicorn): os contadores vêm dos arquivos do diretório multiprocesso, e os
    # gauges lidos do banco precisam ser somados à parte.
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))

    body = Client().get("/metrics").content.decode()

    assert 'orderflow_outbox_pending{measure="count"}' in body
    assert 'orderflow_dependency_up{dependency="database"}' in body
