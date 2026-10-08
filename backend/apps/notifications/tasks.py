from typing import Any
from uuid import UUID

from celery import shared_task

from apps.notifications.application.sending import (
    requeue_stale_notifications,
    send_notification,
)
from apps.notifications.domain.kinds import NotificationStatus


@shared_task(
    bind=True,
    name="notifications.send",
    queue="notifications",
    acks_late=True,
    max_retries=4,
)
def send(self: Any, notification_id: str) -> str:
    """Fila `notifications`: e-mail lento ou SMTP fora do ar não atrasa pedidos e pagamentos."""
    status = send_notification(UUID(notification_id))
    if status == NotificationStatus.PENDING:  # falha transitória: 30 s, 1, 2, 4 min…
        raise self.retry(countdown=30 * 2**self.request.retries)
    return status


@shared_task(name="maintenance.requeue_stale_notifications", queue="maintenance")
def requeue_stale() -> int:
    return requeue_stale_notifications()
