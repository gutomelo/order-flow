from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.pricing.models import PriceList, PriceListItem


class PriceListSerializer(serializers.ModelSerializer[PriceList]):
    segment = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    is_default = serializers.SerializerMethodField()

    class Meta:
        model = PriceList
        fields = (
            "id",
            "name",
            "segment",
            "is_default",
            "currency",
            "items_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_segment(self, price_list: PriceList) -> dict[str, Any] | None:
        segment = price_list.segment
        if segment is None:
            return None
        return {
            "id": str(segment.id),
            "code": segment.code,
            "name": segment.name,
            "is_active": segment.is_active,
        }

    def get_items_count(self, price_list: PriceList) -> int:
        # A listagem anota a contagem; respostas de escrita contam na hora.
        annotated = getattr(price_list, "items_count", None)
        return int(annotated) if annotated is not None else price_list.items.count()

    def get_is_default(self, price_list: PriceList) -> bool:
        return price_list.segment_id is None


class PriceListCreateSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=120)
    # Vazio/nulo = tabela padrão da organização.
    segment_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class PriceListRenameSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=120)


class PriceListItemSerializer(serializers.ModelSerializer[PriceListItem]):
    product = serializers.SerializerMethodField()

    class Meta:
        model = PriceListItem
        fields = ("id", "product", "unit_price", "created_at", "updated_at")
        read_only_fields = fields

    def get_product(self, item: PriceListItem) -> dict[str, Any]:
        product = item.product
        return {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "is_active": product.is_active,
        }


def _price() -> serializers.DecimalField:
    # PR4: não negativo, 2 casas.
    return serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))


class PriceListItemCreateSerializer(serializers.Serializer[dict[str, Any]]):
    product_id = serializers.UUIDField()
    unit_price = _price()


class PriceListItemUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    unit_price = _price()
