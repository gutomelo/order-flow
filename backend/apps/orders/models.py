import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.catalog.models import Product
from apps.customers.models import Customer, CustomerAddress
from apps.inventory.models import Warehouse
from apps.orders.domain.status import OrderStatus
from shared.domain.money import DEFAULT_CURRENCY
from shared.tenancy.models import TenantScopedModel

_STATUS_CHOICES = [(s.value, s.value) for s in OrderStatus]


def _money(**kwargs: Any) -> models.DecimalField[Any, Any]:
    """NUMERIC(14,2): dinheiro nunca é float (CLAUDE.md, regra 4)."""
    return models.DecimalField(max_digits=14, decimal_places=2, **kwargs)


class OrderNumberSequence(TenantScopedModel):
    """Contador de números de pedido por organização (O7): incrementado com a linha bloqueada,
    dentro da transação da submissão — rollback devolve o número, então não há lacunas."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "orders_number_sequence"
        constraints = [
            models.UniqueConstraint(fields=["organization"], name="orders_number_sequence_org_uniq")
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}: {self.last_value}"


class Order(TenantScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Atribuído na submissão; rascunhos (e rascunhos cancelados) não têm número.
    number = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=_STATUS_CHOICES)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="+")
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # Escolha do endereço (rascunho); a cópia congelada fica em `shipping_snapshot`.
    shipping_address = models.ForeignKey(
        CustomerAddress, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    shipping_snapshot = models.JSONField(null=True, blank=True)
    purchase_order_number = models.CharField(max_length=60, blank=True)
    notes = models.CharField(max_length=1000, blank=True)
    subtotal = _money(default=0)
    discount_total = _money(default=0)
    shipping_total = _money(default=0)
    total = _money(default=0)
    currency = models.CharField(max_length=3, default=DEFAULT_CURRENCY)
    submitted_at = models.DateTimeField(null=True, blank=True)
    payment_due_at = models.DateTimeField(null=True, blank=True)  # Phase 7 (reserva)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_order"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"], name="orders_org_number_uniq"
            ),
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in OrderStatus]),
                name="orders_order_status_check",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0)
                & Q(discount_total__gte=0)
                & Q(shipping_total__gte=0)
                & Q(total__gte=0),
                name="orders_order_amounts_non_negative_check",
            ),
            models.CheckConstraint(  # O5
                condition=Q(total=F("subtotal") - F("discount_total") + F("shipping_total")),
                name="orders_order_total_check",
            ),
            models.CheckConstraint(  # todo pedido que saiu do rascunho foi numerado e copiado
                condition=Q(status__in=[OrderStatus.DRAFT, OrderStatus.CANCELLED])
                | (
                    Q(number__isnull=False)
                    & Q(submitted_at__isnull=False)
                    & Q(shipping_snapshot__isnull=False)
                    & Q(warehouse__isnull=False)
                ),
                name="orders_order_submitted_fields_check",
            ),
            models.CheckConstraint(condition=Q(currency="BRL"), name="orders_order_currency_check"),
        ]
        indexes = [
            models.Index(fields=["organization", "status"], name="orders_org_status_idx"),
            models.Index(fields=["organization", "customer"], name="orders_org_customer_idx"),
            models.Index(fields=["organization", "-created_at"], name="orders_org_created_idx"),
        ]

    def __str__(self) -> str:
        return f"#{self.number}" if self.number else f"draft {self.id}"


class OrderLine(TenantScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    position = models.PositiveSmallIntegerField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="+")
    # Snapshot (preço e identificação congelados na submissão).
    sku = models.CharField(max_length=64)
    product_name = models.CharField(max_length=200)
    quantity = models.IntegerField()
    unit_price = _money()
    discount_amount = _money(default=0)
    line_total = _money()
    price_source = models.CharField(max_length=10)

    class Meta:
        db_table = "orders_order_line"
        ordering = ("position",)
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="orders_line_product_uniq"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="orders_line_quantity_check"),
            models.CheckConstraint(  # O3
                condition=Q(unit_price__gte=0)
                & Q(discount_amount__gte=0)
                & Q(discount_amount__lte=F("quantity") * F("unit_price")),
                name="orders_line_amounts_check",
            ),
            models.CheckConstraint(  # O4
                condition=Q(line_total=F("quantity") * F("unit_price") - F("discount_amount")),
                name="orders_line_total_check",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} x{self.quantity}"


class OrderStatusHistory(TenantScopedModel):
    """Toda transição de status (O9). Append-only: trigger rejeita UPDATE/DELETE."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="history")
    # NULL = criação do pedido ("—" na tabela de transições); "" não é um status.
    from_status = models.CharField(  # noqa: DJ001
        max_length=20, choices=_STATUS_CHOICES, null=True
    )
    to_status = models.CharField(max_length=20, choices=_STATUS_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    changed_at = models.DateTimeField(default=timezone.now)
    reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "orders_status_history"
        ordering = ("changed_at", "id")

    def __str__(self) -> str:
        return f"{self.from_status} → {self.to_status}"
