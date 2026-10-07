from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.domain.permissions import Permission
from apps.notifications.api.serializers import NotificationSerializer
from apps.notifications.application.queries import notifications_for
from shared.permissions import HasPermission
from shared.tenancy.api import organization_id_of


class OrderNotificationsView(APIView):
    """Avisos enviados ao cliente sobre um pedido. Escopo da organização: id de outra organização
    devolve lista vazia, sem revelar nada (anti-IDOR)."""

    permission_classes = (IsAuthenticated, HasPermission(Permission.ORDERS_READ))

    @extend_schema(responses=NotificationSerializer(many=True))
    def get(self, request: Request, order_id: UUID) -> Response:
        items = notifications_for(organization_id_of(request), order_id)
        return Response(NotificationSerializer(items, many=True).data)
