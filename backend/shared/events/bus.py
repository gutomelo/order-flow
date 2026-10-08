"""Publicação via outbox e entrega at-least-once com deduplicação (ADR-011).

publish(evento)          dentro da transação do caso de uso → linha em `events_outbox`
relay_pending()          Beat: pendentes (SKIP LOCKED) → uma entrega por handler
deliver(id, handler)     task: aplica o handler uma única vez por (evento, handler)
"""

from collections.abc import Callable
from typing import Any

import structlog
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from opentelemetry import propagate, trace
from prometheus_client import Counter

from shared.events.base import DomainEvent, EventEnvelope
from shared.events.models import OutboxEvent, ProcessedEvent

logger = structlog.get_logger(__name__)

Handler = Callable[[EventEnvelope], None]
Dispatch = Callable[[str, str], Any]

tracer = trace.get_tracer(__name__)

DELIVERIES = Counter(
    "orderflow_events_deliveries_total",
    "Entregas de eventos do outbox por handler e resultado",
    ["event_name", "outcome"],
)

_subscriptions: dict[str, list[str]] = {}  # evento → nomes dos handlers
_handlers: dict[str, Handler] = {}  # nome → handler


def handler_name(handler: Handler) -> str:
    return f"{handler.__module__}.{handler.__qualname__}"


def subscribe(event_name: str) -> Callable[[Handler], Handler]:
    """Registra um handler (importado no `ready()` do app consumidor)."""

    def register(handler: Handler) -> Handler:
        name = handler_name(handler)
        _handlers[name] = handler
        names = _subscriptions.setdefault(event_name, [])
        if name not in names:
            names.append(name)
        return handler

    return register


def handlers_for(event_name: str) -> list[str]:
    return list(_subscriptions.get(event_name, []))


def publish(event: DomainEvent) -> None:
    """Grava o evento junto com a mudança: rollback ⇒ evento nunca existiu."""
    if not connection.in_atomic_block:
        raise RuntimeError("publish() precisa de uma transação: o evento vai junto com a mudança.")
    OutboxEvent.objects.create(
        id=event.event_id,
        event_name=event.event_name,
        version=event.version,
        payload=event.payload(),
        occurred_at=event.occurred_at,
    )


def relay_pending(dispatch: Dispatch, *, batch_size: int = 100) -> int:
    """Encaminha eventos não publicados. `SKIP LOCKED`: relays sobrepostos não se esperam.

    Falha ao enfileirar desfaz o lote (tenta de novo na próxima execução); sucesso no envio com
    falha no commit gera reentrega — por isso `deliver` deduplica.
    """
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(published_at__isnull=True)
            .order_by("occurred_at")[:batch_size]
        )
        now = timezone.now()
        for event in events:
            for name in handlers_for(event.event_name):
                dispatch(str(event.id), name)
            event.published_at = now
        OutboxEvent.objects.bulk_update(events, ["published_at"])
    if events:
        logger.info("events.outbox.relayed", count=len(events))
    return len(events)


def deliver(event_id: str, name: str) -> bool:
    """Aplica um handler a um evento uma única vez (o registro e o efeito no mesmo commit)."""
    handler = _handlers.get(name)
    if handler is None:
        logger.error("events.handler.unknown", handler=name, event_id=event_id)
        return False
    event = OutboxEvent.objects.get(id=event_id)
    envelope = EventEnvelope(
        event_id=event.id,
        event_name=event.event_name,
        version=event.version,
        occurred_at=event.occurred_at,
        payload=event.payload,
    )
    payload = event.payload
    # Mesmo fluxo da origem: logs com o correlation_id da requisição e span filho do trace dela.
    with (
        structlog.contextvars.bound_contextvars(
            correlation_id=payload.get("correlation_id") or event_id,
            request_id=payload.get("request_id") or None,
        ),
        tracer.start_as_current_span(
            f"event {event.event_name}",
            context=propagate.extract(payload.get("trace_context") or {}),
            kind=trace.SpanKind.CONSUMER,
            attributes={"orderflow.event_id": event_id, "orderflow.handler": name},
        ),
    ):
        with transaction.atomic():
            try:
                with transaction.atomic():
                    ProcessedEvent.objects.create(event_id=event.id, handler=name)
            except IntegrityError:
                logger.info("events.delivery.duplicate", handler=name, event_id=event_id)
                DELIVERIES.labels(event_name=event.event_name, outcome="duplicate").inc()
                return False
            handler(envelope)
        DELIVERIES.labels(event_name=event.event_name, outcome="delivered").inc()
        logger.info("events.delivery.done", handler=name, event_name=event.event_name)
    return True
