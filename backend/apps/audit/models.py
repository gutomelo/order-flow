import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.audit.domain.entries import AuditAction, EntityType
from shared.tenancy.models import TenantScopedModel


def _values(enum: type[AuditAction] | type[EntityType]) -> list[str]:
    return sorted(item.value for item in enum)  # ordenado: migrations estáveis


class AuditLog(TenantScopedModel):
    """Registro imutável de uma operação (docs/domain/audit.md). Append-only no banco (trigger):
    só a limpeza de retenção apaga, e só dentro da transação dela."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=40, choices=[(v, v) for v in _values(AuditAction)])
    entity_type = models.CharField(max_length=20, choices=[(v, v) for v in _values(EntityType)])
    entity_id = models.UUIDField()
    entity_label = models.CharField(max_length=120)  # "#000003", "COLA · CD-SP"
    order_id = models.UUIDField(null=True, blank=True)  # pedido relacionado (busca por pedido)
    actor = models.ForeignKey(  # None = sistema (jobs, provedor, reconciliação)
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    reason = models.CharField(max_length=500, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField()  # quando a operação aconteceu (do evento)
    recorded_at = models.DateTimeField(auto_now_add=True)
    request_id = models.CharField(max_length=64, blank=True)
    source_event_id = models.UUIDField(unique=True)  # A1: um registro por evento

    class Meta:
        db_table = "audit_log"
        ordering = ("-occurred_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(action__in=_values(AuditAction)), name="audit_action_check"
            ),
            models.CheckConstraint(
                condition=Q(entity_type__in=_values(EntityType)), name="audit_entity_type_check"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "-occurred_at"], name="audit_org_occurred_idx"),
            models.Index(
                fields=["organization", "entity_type", "entity_id"], name="audit_org_entity_idx"
            ),
            models.Index(fields=["organization", "order_id"], name="audit_org_order_idx"),
            models.Index(fields=["occurred_at"], name="audit_retention_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_label}"
