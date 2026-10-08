"""Fila do outbox lida na hora da coleta (ADR-015): o que ainda não foi encaminhado e há quanto
tempo o mais antigo espera. Atraso crescente = relay parado ou broker bloqueado."""

from collections.abc import Iterable

from django.db.models import Min
from django.utils import timezone

from shared.events.models import OutboxEvent
from shared.observability.metrics import GaugeSample, register_gauges


def _pending() -> Iterable[GaugeSample]:
    pending = OutboxEvent.objects.filter(published_at__isnull=True)
    oldest = pending.aggregate(oldest=Min("occurred_at"))["oldest"]
    age = (timezone.now() - oldest).total_seconds() if oldest else 0.0
    yield {"measure": "count"}, float(pending.count())
    yield {"measure": "oldest_age_seconds"}, age


def register() -> None:
    register_gauges(
        "orderflow_outbox_pending",
        "Eventos ainda não encaminhados pelo relay (quantidade e idade do mais antigo)",
        ["measure"],
        _pending,
    )
