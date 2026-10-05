from typing import Any

from rest_framework import serializers

from apps.customers.models import (
    BrazilianState,
    Customer,
    CustomerAddress,
    CustomerContact,
    CustomerSegment,
)
from shared.domain.documents import format_cnpj


class SegmentSerializer(serializers.ModelSerializer[CustomerSegment]):
    active_customers = serializers.SerializerMethodField()

    class Meta:
        model = CustomerSegment
        fields = (
            "id",
            "code",
            "name",
            "description",
            "active_customers",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_active_customers(self, segment: CustomerSegment) -> int:
        # A listagem anota a contagem (uma query só); respostas de escrita contam na hora.
        annotated = getattr(segment, "active_customers", None)
        if annotated is not None:
            return int(annotated)
        return segment.customers.filter(is_active=True).count()


class SegmentCreateSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(max_length=30)
    name = serializers.CharField(max_length=120)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)


class SegmentUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    # O código é imutável (SG1): não faz parte da edição.
    name = serializers.CharField(max_length=120, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)


class SegmentSummarySerializer(serializers.ModelSerializer[CustomerSegment]):
    class Meta:
        model = CustomerSegment
        fields = ("id", "code", "name", "is_active")
        read_only_fields = fields


class CustomerSerializer(serializers.ModelSerializer[Customer]):
    display_name = serializers.CharField(read_only=True)
    tax_id_formatted = serializers.SerializerMethodField()
    segment = SegmentSummarySerializer(read_only=True, allow_null=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "legal_name",
            "trade_name",
            "display_name",
            "tax_id",
            "tax_id_formatted",
            "email",
            "phone",
            "segment",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_tax_id_formatted(self, customer: Customer) -> str:
        return format_cnpj(customer.tax_id)


class CustomerWriteSerializer(serializers.Serializer[dict[str, Any]]):
    legal_name = serializers.CharField(max_length=200)
    trade_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    # Aceita com ou sem máscara; a validação de dígitos é do serviço (regra CU1).
    tax_id = serializers.CharField(max_length=18)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    segment_id = serializers.UUIDField(required=False, allow_null=True)


class AddressSerializer(serializers.ModelSerializer[CustomerAddress]):
    class Meta:
        model = CustomerAddress
        fields = (
            "id",
            "label",
            "postal_code",
            "street",
            "number",
            "complement",
            "district",
            "city",
            "state",
            "is_billing",
            "is_default_shipping",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AddressWriteSerializer(serializers.Serializer[dict[str, Any]]):
    # O metaclass do DRF trata o campo declarado; só os stubs confundem com `Field.label`.
    label = serializers.CharField(max_length=60)  # type: ignore[assignment]
    # Aceita "01310-100" ou "01310100"; a regra dos 8 dígitos é do serviço (AD1).
    postal_code = serializers.CharField(max_length=10)
    street = serializers.CharField(max_length=200)
    number = serializers.CharField(max_length=20)
    complement = serializers.CharField(max_length=100, required=False, allow_blank=True)
    district = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=100)
    state = serializers.ChoiceField(choices=BrazilianState.choices)


class ContactSerializer(serializers.ModelSerializer[CustomerContact]):
    class Meta:
        model = CustomerContact
        fields = (
            "id",
            "name",
            "job_title",
            "email",
            "phone",
            "is_primary",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ContactWriteSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=120)
    job_title = serializers.CharField(max_length=80, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
