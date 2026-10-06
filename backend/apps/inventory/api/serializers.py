from typing import Any

from rest_framework import serializers

from apps.inventory.models import StockItem, StockMovement, StockReceipt, Warehouse


class WarehouseSerializer(serializers.ModelSerializer[Warehouse]):
    class Meta:
        model = Warehouse
        fields = ("id", "code", "name", "is_active", "created_at", "updated_at")
        read_only_fields = fields


class WarehouseCreateSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=120)


class WarehouseUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    """O código não muda depois de criado (identifica o depósito em etiquetas e integrações)."""

    name = serializers.CharField(max_length=120)


class _ProductRefSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    sku = serializers.CharField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()


class _WarehouseRefSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()


class StockItemSerializer(serializers.ModelSerializer[StockItem]):
    product = _ProductRefSerializer(read_only=True)
    warehouse = _WarehouseRefSerializer(read_only=True)
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = StockItem
        fields = (
            "id",
            "product",
            "warehouse",
            "on_hand",
            "reserved",
            "available",
            "reorder_point",
            "is_low_stock",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_low_stock(self, item: StockItem) -> bool:
        return item.reorder_point > 0 and item.available <= item.reorder_point


class StockItemUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    reorder_point = serializers.IntegerField(min_value=0, max_value=1_000_000)


class _UserRefSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    full_name = serializers.CharField()


class StockMovementSerializer(serializers.ModelSerializer[StockMovement]):
    product = _ProductRefSerializer(source="stock_item.product", read_only=True)
    warehouse = _WarehouseRefSerializer(source="stock_item.warehouse", read_only=True)
    performed_by = _UserRefSerializer(read_only=True, allow_null=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "type",
            "product",
            "warehouse",
            "on_hand_delta",
            "reserved_delta",
            "on_hand_after",
            "reserved_after",
            "reference_type",
            "reference_id",
            "reason",
            "performed_by",
            "created_at",
        )
        read_only_fields = fields


class ReceiptLineSerializer(serializers.Serializer[dict[str, Any]]):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)


class ReceiptCreateSerializer(serializers.Serializer[dict[str, Any]]):
    warehouse_id = serializers.UUIDField()
    supplier_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    document_number = serializers.CharField(
        max_length=60, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = ReceiptLineSerializer(many=True, min_length=1, max_length=200)  # type: ignore[call-arg]

    def validate_lines(self, lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        product_ids = [line["product_id"] for line in lines]
        if len(product_ids) != len(set(product_ids)):  # R1
            raise serializers.ValidationError("Cada produto deve aparecer uma única vez.")
        return lines


class ReceiptSerializer(serializers.ModelSerializer[StockReceipt]):
    movements = serializers.SerializerMethodField()

    class Meta:
        model = StockReceipt
        fields = (
            "id",
            "warehouse_id",
            "supplier_id",
            "document_number",
            "notes",
            "created_at",
            "movements",
        )
        read_only_fields = fields

    def get_movements(self, receipt: StockReceipt) -> list[dict[str, Any]]:
        movements = self.context.get("movements", [])
        return [StockMovementSerializer(m).data for m in movements]


class AdjustmentCreateSerializer(serializers.Serializer[dict[str, Any]]):
    stock_item_id = serializers.UUIDField()
    counted_quantity = serializers.IntegerField(min_value=0, max_value=1_000_000)
    expected_on_hand = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(min_length=5, max_length=500)  # A1


class TransferCreateSerializer(serializers.Serializer[dict[str, Any]]):
    stock_item_id = serializers.UUIDField()
    to_warehouse_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class AvailabilityQuerySerializer(serializers.Serializer[dict[str, Any]]):
    warehouse = serializers.UUIDField()
    products = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=200)


class AvailabilitySerializer(serializers.Serializer[dict[str, Any]]):
    product_id = serializers.UUIDField()
    on_hand = serializers.IntegerField()
    reserved = serializers.IntegerField()
    available = serializers.IntegerField()
