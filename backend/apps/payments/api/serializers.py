from rest_framework import serializers

from apps.payments.models import Payment, Refund


class RefundSerializer(serializers.ModelSerializer[Refund]):
    class Meta:
        model = Refund
        fields = (
            "id",
            "status",
            "amount",
            "reason",
            "failure_reason",
            "attempts",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer[Payment]):
    refunds = RefundSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "order_id",
            "order_reference",
            "method",
            "status",
            "amount",
            "currency",
            "decline_reason",
            "manual_reference",
            "completed_at",
            "created_at",
            "refunds",
        )
        read_only_fields = fields
