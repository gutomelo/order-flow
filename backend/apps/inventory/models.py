import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.inventory.domain.movements import MovementType
from apps.inventory.domain.reservations import HOLDING, ReservationStatus
from shared.tenancy.models import TenantScopedModel

WAREHOUSE_CODE_PATTERN = r"^[A-Z0-9-]{2,20}$"


class Warehouse(TenantScopedModel):
    """Local físico de armazenagem."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_warehouse"
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="inventory_warehouse_org_code_uniq"
            ),
            models.CheckConstraint(
                condition=Q(code__regex=WAREHOUSE_CODE_PATTERN),
                name="inventory_warehouse_code_format_check",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class StockItem(TenantScopedModel):
    """Saldo de um produto em um depósito. Só muda pelo ledger (application/ledger.py)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="+")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stock_items")
    on_hand = models.IntegerField(default=0)
    reserved = models.IntegerField(default=0)
    # Calculado pelo PostgreSQL: impossível divergir de on_hand - reserved e indexável para
    # "estoque baixo" (docs/domain/inventory.md, decisão sobre `available`).
    available = models.GeneratedField(
        expression=F("on_hand") - F("reserved"),
        output_field=models.IntegerField(),
        db_persist=True,
    )
    reorder_point = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_stock_item"
        ordering = ("warehouse__code",)
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"], name="inventory_stock_item_product_warehouse_uniq"
            ),
            models.CheckConstraint(
                condition=Q(on_hand__gte=0), name="inventory_stock_item_on_hand_non_negative_check"
            ),
            models.CheckConstraint(
                condition=Q(reserved__gte=0),
                name="inventory_stock_item_reserved_non_negative_check",
            ),
            models.CheckConstraint(
                condition=Q(reserved__lte=F("on_hand")),
                name="inventory_stock_item_reserved_lte_on_hand_check",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "warehouse"], name="inventory_stock_org_wh_idx"),
            models.Index(
                fields=["organization", "available"], name="inventory_stock_available_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}@{self.warehouse_id}"


class StockReceipt(TenantScopedModel):
    """Documento de entrada de mercadoria; cada linha é um movimento PURCHASE."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="receipts")
    supplier = models.ForeignKey(
        "suppliers.Supplier", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    document_number = models.CharField(max_length=60, blank=True, default="")
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_stock_receipt"
        ordering = ("-created_at",)
        constraints = [
            # R3: a mesma nota do mesmo fornecedor não entra duas vezes.
            models.UniqueConstraint(
                fields=["organization", "supplier", "document_number"],
                condition=~Q(document_number=""),
                nulls_distinct=False,
                name="inventory_receipt_org_supplier_document_uniq",
            ),
        ]


class StockMovement(TenantScopedModel):
    """Registro imutável de toda alteração de saldo (append-only, garantido por trigger)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="movements")
    type = models.CharField(max_length=20, choices=[(t.value, t.value) for t in MovementType])
    on_hand_delta = models.IntegerField()
    reserved_delta = models.IntegerField()
    on_hand_after = models.IntegerField()
    reserved_after = models.IntegerField()
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    reason = models.TextField(blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    request_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_stock_movement"
        ordering = ("-created_at",)
        constraints = [
            # I5: todo movimento altera algo.
            models.CheckConstraint(
                condition=~(Q(on_hand_delta=0) & Q(reserved_delta=0)),
                name="inventory_movement_nonzero_check",
            ),
            models.CheckConstraint(
                condition=Q(type__in=[t.value for t in MovementType]),
                name="inventory_movement_type_check",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"], name="inventory_movement_recent_idx"
            ),
            models.Index(fields=["stock_item", "-created_at"], name="inventory_movement_item_idx"),
            models.Index(
                fields=["reference_type", "reference_id"], name="inventory_movement_ref_idx"
            ),
        ]


class StockReservation(TenantScopedModel):
    """Unidades comprometidas com uma linha de pedido (docs/domain/inventory.md).

    `order_id`/`order_line_id` são referências **opacas**: inventory não conhece pedidos
    (a dependência é sempre orders → inventory).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="reservations")
    order_id = models.UUIDField()
    order_line_id = models.UUIDField()
    quantity = models.IntegerField()
    status = models.CharField(
        max_length=20, choices=[(s.value, s.value) for s in ReservationStatus]
    )
    expires_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_stock_reservation"
        constraints = [
            models.CheckConstraint(  # I5
                condition=Q(quantity__gt=0), name="inventory_reservation_quantity_check"
            ),
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in ReservationStatus]),
                name="inventory_reservation_status_check",
            ),
            models.UniqueConstraint(  # I8
                fields=["order_line_id", "stock_item"],
                # Ordenado: um frozenset mudaria a ordem (e a migration) a cada execução.
                condition=Q(status__in=sorted(s.value for s in HOLDING)),
                name="inventory_reservation_one_holding_per_line_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["order_id"], name="inventory_resv_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.order_line_id}: {self.quantity} ({self.status})"
