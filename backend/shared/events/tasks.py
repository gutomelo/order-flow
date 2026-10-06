from datetime import timedelta

import structlog
from celery import shared_task
from django.utils import timezone

from shared.events.bus import deliver, relay_pending
from shared.events.models import OutboxEvent

logger = structlog.get_logger(__name__)

RETENTION = timedelta(days=30)


# Erro em handler: retry exponencial; esgotado, a entrega fica sem `ProcessedEvent` e pode ser
# reenfileirada manualmente com segurança (o handler é idempotente).
@shared_task(
    name="events.deliver",
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=8,
)
def deliver_event(event_id: str, handler: str) -> bool:
    return deliver(event_id, handler)


@shared_task(name="events.relay_outbox")
def relay_outbox() -> int:
    return relay_pending(deliver_event.delay)


@shared_task(name="maintenance.purge_published_events", queue="maintenance")
def purge_published_events() -> int:
    removed, _ = OutboxEvent.objects.filter(
        published_at__lte=timezone.now() - RETENTION
    ).delete()  # ProcessedEvent cai junto (CASCADE)
    logger.info("events.outbox.purged", removed=removed)
    return removed
