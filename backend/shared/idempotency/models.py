import uuid

from django.conf import settings
from django.db import models


class IdempotencyStatus(models.TextChoices):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class IdempotencyRecord(models.Model):
    """Resposta de uma operação protegida, por (usuário, operação, chave).

    Dado técnico temporário: removido após `expires_at` (docs/architecture/domain-model.md).
    `IN_PROGRESS` só fica visível para outras transações em operações de várias transações
    (pagamento, Phase 8); nas de uma transação o registro nasce e conclui no mesmo commit.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        settings.TENANT_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    operation = models.CharField(max_length=60)
    key = models.UUIDField()
    fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=IdempotencyStatus.choices)
    response_status = models.PositiveSmallIntegerField(null=True)
    response_body = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "idempotency_record"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "operation", "key"], name="idempotency_record_user_op_key_uniq"
            ),
        ]
        indexes = [models.Index(fields=["expires_at"], name="idempotency_expires_idx")]

    def __str__(self) -> str:
        return f"{self.operation}:{self.key}"
