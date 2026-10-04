from typing import Any

from rest_framework import serializers

from apps.catalog.models import Category, Product, UnitOfMeasure
from apps.catalog.selectors import category_path


class CategorySummarySerializer(serializers.ModelSerializer[Category]):
    path = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "path", "is_active")
        read_only_fields = fields

    def get_path(self, category: Category) -> str:
        return category_path(category)


class CategorySerializer(serializers.ModelSerializer[Category]):
    """Nó da árvore achatada: `path` vem do contexto (montado em uma consulta)."""

    parent_id = serializers.UUIDField(read_only=True, allow_null=True)
    path = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "parent_id", "depth", "path", "is_active")
        read_only_fields = fields

    def get_path(self, category: Category) -> str:
        paths: dict[Any, str] = self.context.get("paths", {})
        return paths.get(category.id) or category_path(category)


class CategoryWriteSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=100)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class SupplierSummarySerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    display_name = serializers.CharField()
    is_active = serializers.BooleanField()


class ProductSerializer(serializers.ModelSerializer[Product]):
    category = CategorySummarySerializer(read_only=True, allow_null=True)
    default_supplier = SupplierSummarySerializer(read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "sku",
            "name",
            "description",
            "unit",
            "barcode",
            "category",
            "default_supplier",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProductCreateSerializer(serializers.Serializer[dict[str, Any]]):
    sku = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    unit = serializers.ChoiceField(choices=UnitOfMeasure.values, default=UnitOfMeasure.UNIT)
    barcode = serializers.CharField(max_length=14, required=False, allow_blank=True, default="")
    category_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    default_supplier_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class ProductUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    """Sem `sku`: a identidade de negócio do produto não muda (regra C7)."""

    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    unit = serializers.ChoiceField(choices=UnitOfMeasure.values, required=False)
    barcode = serializers.CharField(max_length=14, required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    default_supplier_id = serializers.UUIDField(required=False, allow_null=True)
