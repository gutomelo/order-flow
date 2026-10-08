import structlog
from celery import shared_task

from apps.inventory.application.reconciliation import find_divergences

logger = structlog.get_logger(__name__)


@shared_task(name="maintenance.reconcile_stock", queue="maintenance")
def reconcile_stock() -> int:
    """Compara saldos com reservas e movimentos (I6, I7). Só lê: rodar duas vezes é inofensivo."""
    divergences = find_divergences()
    for divergence in divergences:
        logger.error(
            "inventory.reconciliation.divergence",
            stock_item_id=str(divergence.stock_item_id),
            field=divergence.field,
            stored=divergence.stored,
            expected=divergence.expected,
        )
    logger.info("inventory.reconciliation.completed", divergences=len(divergences))
    return len(divergences)
