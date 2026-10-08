import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from opentelemetry import propagate

from shared.logging import get_correlation_id, get_request_id


def _current_request_id() -> str:
    # Liga o evento à requisição que o originou (auditoria, logs); vazio em jobs do sistema.
    return get_request_id() or ""


def _current_correlation_id() -> str:
    return get_correlation_id() or ""


def _current_trace_context() -> dict[str, str]:
    """`traceparent` do span atual (W3C): o trace continua na entrega do evento (ADR-015)."""
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Fato ocorrido, no passado e imutável (`OrderPaid`, `PaymentRefunded`).

    Payload: só o necessário, com tipos simples (UUID e Decimal viram texto). Quem precisar de mais
    consulta o módulo dono pelo ID (docs/architecture/event-driven.md).
    """

    event_name: ClassVar[str]
    version: ClassVar[int] = 1

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=timezone.now)
    request_id: str = field(default_factory=_current_request_id)
    correlation_id: str = field(default_factory=_current_correlation_id)
    trace_context: dict[str, str] = field(default_factory=_current_trace_context)

    def payload(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("event_id")
        data.pop("occurred_at")
        result: dict[str, Any] = json.loads(json.dumps(data, cls=DjangoJSONEncoder))
        return result


@dataclass(frozen=True)
class EventEnvelope:
    """O que o handler recebe: o evento como foi gravado no outbox."""

    event_id: UUID
    event_name: str
    version: int
    occurred_at: datetime
    payload: dict[str, Any]
