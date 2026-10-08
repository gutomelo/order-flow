from typing import Any
from uuid import UUID

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.domain.permissions import Permission
from apps.payments.api.serializers import PaymentSerializer, RefundSerializer
from apps.payments.application import refunds
from apps.payments.models import Payment
from shared.idempotency.decorators import HEADER, idempotent
from shared.permissions import HasPermission
from shared.tenancy.api import TenantScopedQuerysetMixin, organization_id_of

_IDEMPOTENCY_HEADER = OpenApiParameter(
    HEADER, OpenApiTypes.UUID, OpenApiParameter.HEADER, required=True
)


def _actor_id(request: Request) -> UUID:
    user: Any = request.user
    return UUID(str(user.id))


class PaymentViewSet(
    TenantScopedQuerysetMixin, mixins.ListModelMixin, viewsets.GenericViewSet[Payment]
):
    """Pagamentos e estornos da organização — visão do financeiro."""

    queryset = Payment.objects.prefetch_related("refunds")
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated, HasPermission(Permission.PAYMENTS_READ))
    filterset_fields = ("status", "method", "order_id")
    search_fields = ("order_reference", "manual_reference")
    ordering = ("-created_at",)


class RefundRetryView(APIView):
    permission_classes = (IsAuthenticated, HasPermission(Permission.PAYMENTS_REFUND))

    @extend_schema(request=None, responses=RefundSerializer, parameters=[_IDEMPOTENCY_HEADER])
    @idempotent("payments.refund_retry")
    def post(self, request: Request, refund_id: UUID) -> Response:
        refund = refunds.retry_refund(organization_id_of(request), _actor_id(request), refund_id)
        return Response(RefundSerializer(refund).data)


class RefundConfirmView(APIView):
    permission_classes = (IsAuthenticated, HasPermission(Permission.PAYMENTS_REFUND))

    @extend_schema(request=None, responses=RefundSerializer, parameters=[_IDEMPOTENCY_HEADER])
    @idempotent("payments.refund_confirm")
    def post(self, request: Request, refund_id: UUID) -> Response:
        refund = refunds.confirm_manual_refund(
            organization_id_of(request), _actor_id(request), refund_id
        )
        return Response(RefundSerializer(refund).data)
