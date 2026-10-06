import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.payments.domain.status import PaymentMethod, PaymentStatus, RefundStatus
from shared.domain.money import DEFAULT_CURRENCY
from shared.tenancy.models import TenantScopedModel


def _choices(enum: Any) -> list[tuple[str, str]]:
    return [(item.value, item.value) for item in enum]


def _values(enum: Any) -> list[str]:
    return sorted(item.value for item in enum)  # ordenado: migrations estáveis


class Payment(TenantScopedModel):
    """Cobrança de um pedido (docs/domain/payments.md). Nunca removida (P6).

    Não guarda token nem dados de cartão (P4): só valor, status e referências.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField()  # referência opaca: payments não conhece pedidos
    order_reference = models.CharField(max_length=30)  # ex.: "#000003", para o financeiro
    method = models.CharField(max_length=10, choices=_choices(PaymentMethod))
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default=DEFAULT_CURRENCY)
    status = models.CharField(max_length=10, choices=_choices(PaymentStatus))
    # Enviada ao gateway: repetir a cobrança com a mesma chave nunca cobra duas vezes.
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    provider_reference = models.CharField(max_length=100, blank=True)
    decline_reason = models.CharField(max_length=100, blank=True)
    manual_reference = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)  # consultas de reconciliação
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_payment"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(  # P1: nunca cobrar duas vezes o mesmo pedido
                fields=["order_id"],
                condition=Q(status=PaymentStatus.APPROVED),
                name="payments_one_approved_per_order_uniq",
            ),
            models.UniqueConstraint(  # P2: uma tentativa por vez
                fields=["order_id"],
                condition=Q(status=PaymentStatus.PENDING),
                name="payments_one_pending_per_order_uniq",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="payments_amount_positive_check"
            ),
            models.CheckConstraint(
                condition=Q(status__in=_values(PaymentStatus)), name="payments_status_check"
            ),
            models.CheckConstraint(
                condition=Q(method__in=_values(PaymentMethod)), name="payments_method_check"
            ),
            models.CheckConstraint(  # baixa manual sempre identifica o recebimento
                condition=~Q(method=PaymentMethod.MANUAL) | ~Q(manual_reference=""),
                name="payments_manual_reference_check",
            ),
        ]
        indexes = [
            models.Index(fields=["order_id"], name="payments_order_idx"),
            models.Index(  # reconciliação: só cartões pendentes, pelo próximo horário
                fields=["next_attempt_at"],
                condition=Q(status=PaymentStatus.PENDING),
                name="payments_pending_due_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order_reference} {self.method} {self.status}"


class Refund(TenantScopedModel):
    """Estorno total de um pagamento aprovado (P5). Nunca removido (P6)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=_choices(RefundStatus))
    reason = models.CharField(max_length=200, blank=True)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    provider_reference = models.CharField(max_length=100, blank=True)
    failure_reason = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments_refund"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(  # P5: um estorno vivo (ou concluído) por pagamento
                fields=["payment"],
                condition=Q(status__in=[RefundStatus.PENDING, RefundStatus.SUCCEEDED]),
                name="payments_one_active_refund_uniq",
            ),
            models.CheckConstraint(condition=Q(amount__gt=0), name="payments_refund_amount_check"),
            models.CheckConstraint(
                condition=Q(status__in=_values(RefundStatus)), name="payments_refund_status_check"
            ),
        ]

    def __str__(self) -> str:
        return f"refund {self.payment_id} {self.status}"
