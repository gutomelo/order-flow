import uuid
from typing import Any

from django.db import models
from django.db.models import Q

from apps.notifications.domain.kinds import NotificationKind, NotificationStatus
from shared.tenancy.models import TenantScopedModel


def _choices(enum: Any) -> list[tuple[str, str]]:
    return [(item.value, item.value) for item in enum]


def _values(enum: Any) -> list[str]:
    return sorted(item.value for item in enum)  # ordenado: migrations estáveis


class Notification(TenantScopedModel):
    """Um e-mail a enviar (ou já enviado) e o seu histórico (docs/domain/notifications.md).

    Guarda destinatário, assunto e status — **não** guarda o corpo: e-mails de segurança levam
    um link com token, e os demais são remontados dos dados atuais na hora do envio.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=30, choices=_choices(NotificationKind))
    status = models.CharField(max_length=10, choices=_choices(NotificationStatus))
    source_event_id = models.UUIDField()  # evento do outbox que originou o aviso
    reference_id = models.UUIDField()  # pedido, item de estoque ou usuário
    recipient_email = models.EmailField(blank=True)  # dado pessoal: nunca vai para log
    recipient_name = models.CharField(max_length=150, blank=True)
    subject = models.CharField(max_length=200, blank=True)  # gravado no envio
    context = models.JSONField(default=dict, blank=True)  # parâmetros não sensíveis do texto
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=100, blank=True)  # tipo do erro, sem mensagem
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(  # N1: reentrega do evento não duplica o aviso
                fields=["source_event_id", "recipient_email"],
                name="notifications_one_per_event_recipient_uniq",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=_values(NotificationKind)), name="notifications_kind_check"
            ),
            models.CheckConstraint(
                condition=Q(status__in=_values(NotificationStatus)),
                name="notifications_status_check",
            ),
            models.CheckConstraint(  # N2: enviado ⇔ tem data de envio
                condition=Q(status=NotificationStatus.SENT, sent_at__isnull=False)
                | (~Q(status=NotificationStatus.SENT) & Q(sent_at__isnull=True)),
                name="notifications_sent_at_check",
            ),
            models.CheckConstraint(  # N3: só "sem destinatário" fica sem e-mail
                condition=Q(status=NotificationStatus.SKIPPED) | ~Q(recipient_email=""),
                name="notifications_recipient_check",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "reference_id"], name="notifications_reference_idx"
            ),
            models.Index(  # varredura: só pendentes, pelos mais antigos
                fields=["updated_at"],
                condition=Q(status=NotificationStatus.PENDING),
                name="notifications_pending_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.status}"
