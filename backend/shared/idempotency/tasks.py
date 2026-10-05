import structlog
from celery import shared_task
from django.utils import timezone

from shared.idempotency.models import IdempotencyRecord

logger = structlog.get_logger(__name__)

BATCH_SIZE = 1000


@shared_task(name="maintenance.purge_expired_idempotency_records", queue="maintenance")
def purge_expired_idempotency_records() -> int:
    """Remove registros expirados em lotes. Idempotente: rodar de novo só apaga o que sobrou."""
    removed = 0
    while True:
        ids = list(
            IdempotencyRecord.objects.filter(expires_at__lte=timezone.now()).values_list(
                "id", flat=True
            )[:BATCH_SIZE]
        )
        if not ids:
            break
        removed += IdempotencyRecord.objects.filter(id__in=ids).delete()[0]
    logger.info("idempotency.records.purged", removed=removed)
    return removed
