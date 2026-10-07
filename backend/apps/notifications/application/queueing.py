"""Cria o registro do aviso e agenda o envio para depois do commit (docs/domain/notifications.md).

Roda dentro da transação da entrega do evento (`shared.events.bus.deliver`): se ela falhar, nem o
registro nem o envio existem, e a reentrega do evento recomeça do zero.
"""

from typing import Any
from uuid import UUID

import structlog
from celery import current_app
from django.db import transaction

from apps.notifications.domain.kinds import NotificationKind, NotificationStatus
from apps.notifications.models import Notification

logger = structlog.get_logger(__name__)

SEND_TASK = "notifications.send"


def enqueue_send(notification_id: UUID) -> None:
    # Por nome: a camada application não importa o módulo de tasks (que importa ela).
    current_app.send_task(SEND_TASK, args=[str(notification_id)], queue="notifications")


def queue_notification(
    *,
    organization_id: UUID,
    kind: NotificationKind,
    source_event_id: UUID,
    reference_id: UUID,
    recipient_email: str,
    recipient_name: str,
    context: dict[str, Any] | None = None,
) -> Notification:
    status = NotificationStatus.PENDING if recipient_email else NotificationStatus.SKIPPED
    notification = Notification.objects.create(
        organization_id=organization_id,
        kind=kind,
        status=status,
        source_event_id=source_event_id,
        reference_id=reference_id,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        context=context or {},
    )
    if status == NotificationStatus.PENDING:
        transaction.on_commit(lambda: enqueue_send(notification.id))
    logger.info(
        "notifications.notification.queued",
        notification_id=str(notification.id),
        kind=kind.value,
        status=status.value,
    )
    return notification
