import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.shipping.domain.status import DeliverySource, ShipmentStatus
from shared.tenancy.models import TenantScopedModel


def _choices(enum: Any) -> list[tuple[str, str]]:
    return [(item.value, item.value) for item in enum]


def _values(enum: Any) -> list[str]:
    return sorted(item.value for item in enum)  # ordenado: migrations estáveis


class Shipment(TenantScopedModel):
    """Remessa de um pedido (docs/domain/shipping.md). Uma por pedido (S1), nunca removida."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField()  # referência opaca: shipping não conhece pedidos
    order_reference = models.CharField(max_length=30)  # ex.: "#000003", para a logística
    carrier = models.CharField(max_length=60)
    tracking_code = models.CharField(max_length=60)
    status = models.CharField(max_length=12, choices=_choices(ShipmentStatus))
    shipped_at = models.DateTimeField()
    shipped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivery_source = models.CharField(max_length=10, choices=_choices(DeliverySource), blank=True)
    delivered_by = models.ForeignKey(  # só na confirmação manual
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    delivery_note = models.CharField(max_length=200, blank=True)  # ex.: "recebido por Maria"
    last_checked_at = models.DateTimeField(null=True, blank=True)
    next_check_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shipping_shipment"
        ordering = ("-shipped_at",)
        constraints = [
            models.UniqueConstraint(  # S1: uma remessa por pedido
                fields=["order_id"], name="shipping_one_shipment_per_order_uniq"
            ),
            models.UniqueConstraint(
                fields=["carrier", "tracking_code"], name="shipping_tracking_code_uniq"
            ),
            models.CheckConstraint(
                condition=Q(status__in=_values(ShipmentStatus)), name="shipping_status_check"
            ),
            models.CheckConstraint(  # S3: entregue ⇔ data e origem da confirmação
                condition=(
                    Q(
                        status=ShipmentStatus.DELIVERED,
                        delivered_at__isnull=False,
                        delivery_source__in=_values(DeliverySource),
                    )
                    | Q(
                        status=ShipmentStatus.IN_TRANSIT,
                        delivered_at__isnull=True,
                        delivery_source="",
                    )
                ),
                name="shipping_delivery_consistency_check",
            ),
        ]
        indexes = [
            models.Index(  # rastreio: só remessas em trânsito, pelo próximo horário
                fields=["next_check_at"],
                condition=Q(status=ShipmentStatus.IN_TRANSIT),
                name="shipping_in_transit_due_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order_reference} {self.tracking_code} {self.status}"
