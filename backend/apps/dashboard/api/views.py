from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.application.metrics import Audience, dashboard_for
from apps.dashboard.domain.periods import PeriodKey
from apps.identity.domain.permissions import Permission
from shared.permissions import HasPermission
from shared.tenancy.api import organization_id_of


class DashboardQuerySerializer(serializers.Serializer[dict[str, Any]]):
    period = serializers.ChoiceField(
        choices=[key.value for key in PeriodKey], default=PeriodKey.LAST_7_DAYS.value
    )


class DashboardView(APIView):
    """Indicadores da organização. Dinheiro só com `reports:financial`; estoque baixo só com
    `inventory:read` (as seções vêm `null` para quem não pode ver)."""

    permission_classes = (IsAuthenticated, HasPermission(Permission.ORDERS_READ))

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "period", OpenApiTypes.STR, enum=[k.value for k in PeriodKey], required=False
            )
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request: Request) -> Response:
        query = DashboardQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        user: Any = request.user
        audience = Audience(
            money=user.has_api_permission(Permission.REPORTS_FINANCIAL),
            stock=user.has_api_permission(Permission.INVENTORY_READ),
        )
        data = dashboard_for(
            organization_id_of(request), PeriodKey(query.validated_data["period"]), audience
        )
        return Response(data)
