from celery import shared_task

from apps.shipping.application.tracking import track_due_shipments


@shared_task(name="maintenance.track_shipments", queue="integrations", acks_late=True)
def track_shipments() -> int:
    """Fila `integrations`: lentidão da transportadora não atrasa as demais filas."""
    return track_due_shipments()
