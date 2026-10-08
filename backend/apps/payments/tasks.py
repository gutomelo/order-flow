from celery import shared_task

from apps.payments.application.reconciliation import reconcile_pending_payments


@shared_task(name="maintenance.reconcile_pending_payments", queue="integrations", acks_late=True)
def reconcile_payments() -> int:
    """Fila `integrations`: lentidão do provedor não atrasa as demais filas."""
    return reconcile_pending_payments()
