from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.orders.application.queries import Quote
from apps.orders.models import Order, OrderLine, OrderStatusHistory
from shared.domain.documents import format_cnpj


def _money(**kwargs: Any) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=14, decimal_places=2, **kwargs)


def _person(user: Any) -> dict[str, Any] | None:
    return None if user is None else {"id": str(user.id), "name": user.full_name}


class OrderLineSerializer(serializers.ModelSerializer[OrderLine]):
    class Meta:
        model = OrderLine
        fields = (
            "id",
            "product_id",
            "sku",
            "product_name",
            "quantity",
            "unit_price",
            "discount_amount",
            "line_total",
            "price_source",
        )
        read_only_fields = fields


class StatusHistorySerializer(serializers.ModelSerializer[OrderStatusHistory]):
    changed_by = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory
        fields = ("id", "from_status", "to_status", "changed_by", "changed_at", "reason")
        read_only_fields = fields

    def get_changed_by(self, entry: OrderStatusHistory) -> dict[str, Any] | None:
        return _person(entry.changed_by)


class OrderSummarySerializer(serializers.ModelSerializer[Order]):
    customer = serializers.SerializerMethodField()
    lines_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields: tuple[str, ...] = (
            "id",
            "number",
            "status",
            "customer",
            "purchase_order_number",
            "total",
            "currency",
            "lines_count",
            "submitted_at",
            "payment_due_at",
            "created_at",
            "updated_at",
        )
        read_only_fields: tuple[str, ...] = fields

    def get_customer(self, order: Order) -> dict[str, Any]:
        customer = order.customer
        return {
            "id": str(customer.id),
            "display_name": customer.display_name,
            "legal_name": customer.legal_name,
            "tax_id_formatted": format_cnpj(customer.tax_id),
        }

    def get_lines_count(self, order: Order) -> int:
        annotated = getattr(order, "lines_count", None)
        return int(annotated) if annotated is not None else order.lines.count()


class OrderSerializer(OrderSummarySerializer):
    warehouse = serializers.SerializerMethodField()
    shipping = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    lines = OrderLineSerializer(many=True, read_only=True)
    history = StatusHistorySerializer(many=True, read_only=True)

    class Meta(OrderSummarySerializer.Meta):
        fields = (
            *OrderSummarySerializer.Meta.fields,
            "warehouse",
            "shipping_address_id",
            "shipping",
            "notes",
            "subtotal",
            "discount_total",
            "shipping_total",
            "created_by",
            "lines",
            "history",
        )
        read_only_fields = fields

    def get_warehouse(self, order: Order) -> dict[str, Any] | None:
        warehouse = order.warehouse
        if warehouse is None:
            return None
        return {"id": str(warehouse.id), "code": warehouse.code, "name": warehouse.name}

    def get_shipping(self, order: Order) -> dict[str, Any] | None:
        """Cópia congelada (pedido enviado) ou o endereço escolhido atual (rascunho)."""
        if order.shipping_snapshot is not None:
            return dict(order.shipping_snapshot)
        address = order.shipping_address
        if address is None:
            return None
        return {
            "address_id": str(address.id),
            "label": address.label,
            "postal_code": address.postal_code,
            "street": address.street,
            "number": address.number,
            "complement": address.complement,
            "district": address.district,
            "city": address.city,
            "state": address.state,
        }

    def get_created_by(self, order: Order) -> dict[str, Any] | None:
        return _person(order.created_by)


class LineInputSerializer(serializers.Serializer[dict[str, Any]]):
    product_id = serializers.UUIDField()
    # Sem min_value: quantidade < 1 vira INVALID_QUANTITY com os produtos (feedback por linha).
    quantity = serializers.IntegerField(max_value=1_000_000)


def _lines_field(**kwargs: Any) -> serializers.ListField:
    # Um `child` novo por campo: o DRF vincula a instância ao primeiro ListField que a usa.
    return serializers.ListField(child=LineInputSerializer(), max_length=200, **kwargs)


class DraftSerializer(serializers.Serializer[dict[str, Any]]):
    customer_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField(required=False, allow_null=True)
    shipping_address_id = serializers.UUIDField(required=False, allow_null=True)
    purchase_order_number = serializers.CharField(max_length=60, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    lines = _lines_field(required=False)


class PlaceOrderSerializer(serializers.Serializer[dict[str, Any]]):
    customer_id = serializers.UUIDField()
    warehouse_id = serializers.UUIDField(allow_null=True)
    shipping_address_id = serializers.UUIDField(required=False, allow_null=True)
    purchase_order_number = serializers.CharField(max_length=60, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    lines = _lines_field()
    expected_total = _money(required=False, allow_null=True)


class SubmitSerializer(serializers.Serializer[dict[str, Any]]):
    expected_total = _money(required=False, allow_null=True)


class CancelSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField(max_length=500, allow_blank=True)


class QuoteRequestSerializer(serializers.Serializer[dict[str, Any]]):
    customer_id = serializers.UUIDField()
    lines = _lines_field()


class QuoteLineSerializer(serializers.Serializer[dict[str, Any]]):
    product_id = serializers.UUIDField()
    sku = serializers.CharField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = _money()
    line_total = _money()
    price_source = serializers.CharField()


class QuoteSerializer(serializers.Serializer[dict[str, Any]]):
    lines = QuoteLineSerializer(many=True)
    subtotal = _money()
    discount_total = _money()
    shipping_total = _money()
    total = _money()
    currency = serializers.CharField()

    @staticmethod
    def from_quote(quote: Quote) -> dict[str, Any]:
        def amount(value: Any) -> Decimal:
            return Decimal(value.amount)

        return {
            "lines": [
                {
                    "product_id": line.product_id,
                    "sku": line.sku,
                    "product_name": line.product_name,
                    "quantity": line.quantity,
                    "unit_price": amount(line.unit_price),
                    "line_total": amount(line.line_total),
                    "price_source": line.price_source,
                }
                for line in quote.lines
            ],
            "subtotal": amount(quote.totals.subtotal),
            "discount_total": amount(quote.totals.discount_total),
            "shipping_total": amount(quote.totals.shipping_total),
            "total": amount(quote.totals.total),
            "currency": quote.totals.total.currency,
        }
