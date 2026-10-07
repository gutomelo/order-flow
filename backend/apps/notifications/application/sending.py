"""Envio de um aviso (task `notifications.send`) e varredura dos que ficaram para trás.

Exatamente-uma-vez não existe com SMTP; o que dá para garantir:
- dois workers nunca enviam o mesmo aviso ao mesmo tempo (`SKIP LOCKED` + status);
- enviado = `SENT` gravado logo em seguida; se o processo morrer entre os dois, a varredura pode
  reenviar — o `Message-ID` é o id do aviso, e clientes de e-mail descartam a duplicata.
"""

from datetime import timedelta
from email.utils import parseaddr
from smtplib import SMTPException
from uuid import UUID

import structlog
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from apps.notifications.application.queueing import enqueue_send
from apps.notifications.application.rendering import build_email
from apps.notifications.domain.kinds import NotificationStatus
from apps.notifications.models import Notification

logger = structlog.get_logger(__name__)

TRANSIENT_ERRORS = (SMTPException, OSError)
STALE_AFTER = timedelta(minutes=10)


def _message_id(notification: Notification) -> str:
    domain = parseaddr(settings.DEFAULT_FROM_EMAIL)[1].partition("@")[2] or "orderflow.local"
    return f"<{notification.id}@{domain}>"


def send_notification(notification_id: UUID) -> str:
    """Devolve o status final desta tentativa. `PENDING` = falha transitória (tentar de novo)."""
    with transaction.atomic():
        notification = (
            Notification.objects.select_for_update(skip_locked=True)
            .filter(id=notification_id, status=NotificationStatus.PENDING)
            .first()
        )
        if notification is None:  # já enviado/encerrado, ou outro worker está nele
            return "NOOP"
        content = build_email(notification)
        if content is None:
            notification.status = NotificationStatus.SKIPPED
            notification.last_error = "RecipientUnavailable"
            notification.save()
            return notification.status
        notification.attempts += 1
        notification.subject = content.subject[:200]
        try:
            EmailMessage(
                subject=content.subject,
                body=content.body,
                to=[notification.recipient_email],
                headers={"Message-ID": _message_id(notification)},
            ).send()
        except TRANSIENT_ERRORS as exc:
            # Só o tipo do erro: a mensagem do SMTP pode trazer o endereço (dado pessoal).
            notification.last_error = type(exc).__name__
            if notification.attempts >= settings.NOTIFICATIONS_MAX_ATTEMPTS:
                notification.status = NotificationStatus.FAILED
            notification.save()
            logger.warning(
                "notifications.notification.send_failed",
                notification_id=str(notification.id),
                attempts=notification.attempts,
                error=notification.last_error,
            )
            return notification.status
        notification.status = NotificationStatus.SENT
        notification.sent_at = timezone.now()
        notification.last_error = ""
        notification.save()
    logger.info("notifications.notification.sent", notification_id=str(notification_id))
    return NotificationStatus.SENT


def requeue_stale_notifications() -> int:
    """Pendentes parados há mais de `STALE_AFTER` (enfileiramento perdido, worker que morreu,
    retries esgotados na fila): voltam para a fila. Enviar de novo é seguro (ver o módulo)."""
    limit = timezone.now() - STALE_AFTER
    stale = list(
        Notification.objects.filter(
            status=NotificationStatus.PENDING, updated_at__lt=limit
        ).values_list("id", flat=True)[:500]
    )
    for notification_id in stale:
        enqueue_send(notification_id)
    if stale:
        logger.info("notifications.notification.requeued", count=len(stale))
    return len(stale)
