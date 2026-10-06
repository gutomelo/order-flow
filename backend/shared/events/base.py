import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID, uuid4

from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone


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
