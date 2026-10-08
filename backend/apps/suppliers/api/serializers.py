from typing import Any

from rest_framework import serializers

from apps.suppliers.models import Supplier
from shared.domain.documents import format_cnpj


class SupplierSerializer(serializers.ModelSerializer[Supplier]):
    display_name = serializers.CharField(read_only=True)
    tax_id_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = (
            "id",
            "legal_name",
            "trade_name",
            "display_name",
            "tax_id",
            "tax_id_formatted",
            "email",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_tax_id_formatted(self, supplier: Supplier) -> str:
        return format_cnpj(supplier.tax_id)


class SupplierWriteSerializer(serializers.Serializer[dict[str, Any]]):
    legal_name = serializers.CharField(max_length=200)
    trade_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    # Aceita com ou sem máscara; a validação de dígitos é do serviço (regra S1).
    tax_id = serializers.CharField(max_length=18)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
