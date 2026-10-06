import uuid

from django.db import models
from django.db.models import Q


class OutboxEvent(models.Model):
    """Evento de domínio gravado na mesma transação da mudança de negócio (ADR-011).

    O relay publica os pendentes; a linha fica para reprocessamento e auditoria técnica até a
    limpeza periódica.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # = event_id
    event_name = models.CharField(max_length=100)
    version = models.PositiveSmallIntegerField(default=1)
    payload = models.JSONField()
    occurred_at = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "events_outbox"
        indexes = [
            # Relay: só os não publicados, em ordem de ocorrência.
            models.Index(
                fields=["occurred_at"],
                condition=Q(published_at__isnull=True),
                name="events_outbox_pending_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_name} {self.id}"


class ProcessedEvent(models.Model):
    """Entrega já aplicada por um handler: torna o at-least-once idempotente."""

    event = models.ForeignKey(OutboxEvent, on_delete=models.CASCADE, related_name="+")
    handler = models.CharField(max_length=200)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events_processed"
        constraints = [
            models.UniqueConstraint(fields=["event", "handler"], name="events_processed_uniq")
        ]

    def __str__(self) -> str:
        return f"{self.handler} ← {self.event_id}"
