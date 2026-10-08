"""Métricas de avisos (ADR-015): resultados de envio (contador, no worker) e fila atual (lida do
banco na coleta)."""

from collections.abc import Iterable
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from prometheus_client import Counter

from apps.notifications.domain.kinds import NotificationStatus
from apps.notifications.models import Notification
from shared.observability.metrics import GaugeSample, register_gauges

SEND_OUTCOMES = Counter(
    "orderflow_notifications_send_total",
    "Tentativas de envio de e-mail por tipo e resultado",
    ["kind", "outcome"],
)


def _queue() -> Iterable[GaugeSample]:
    since = timezone.now() - timedelta(hours=24)
    rows = (
        Notification.objects.filter(
            status__in=[NotificationStatus.PENDING, NotificationStatus.FAILED],
            updated_at__gte=since,
        )
        .values("status")
        .annotate(total=Count("id"))
    )
    found = {row["status"]: row["total"] for row in rows}
    for status in (NotificationStatus.PENDING, NotificationStatus.FAILED):
        yield {"status": status.value}, float(found.get(status, 0))


def register() -> None:
    register_gauges(
        "orderflow_notifications_last_24h",
        "Avisos pendentes e que falharam (atualizados nas últimas 24 h)",
        ["status"],
        _queue,
    )
