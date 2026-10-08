from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.identity.domain.permissions import Permission
from apps.suppliers import services
from apps.suppliers.api.serializers import SupplierSerializer, SupplierWriteSerializer
from apps.suppliers.models import Supplier
from shared.api.activation import ActivationActionsMixin
from shared.permissions import HasReadWritePermission
from shared.tenancy.api import TenantScopedQuerysetMixin


class SupplierViewSet(
    ActivationActionsMixin,
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Supplier],
):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = (
        IsAuthenticated,
        HasReadWritePermission(read=Permission.SUPPLIERS_READ, write=Permission.SUPPLIERS_MANAGE),
    )
    http_method_names = ("get", "post", "patch", "head", "options")
    filterset_fields = ("is_active",)
    search_fields = ("legal_name", "trade_name", "tax_id", "email")
    ordering_fields = ("legal_name", "trade_name", "created_at")
    ordering = ("legal_name",)

    @extend_schema(request=SupplierWriteSerializer, responses={201: SupplierSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = SupplierWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = services.create_supplier(
            self.organization_id, services.SupplierData(**serializer.validated_data)
        )
        return Response(SupplierSerializer(supplier).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=SupplierWriteSerializer, responses=SupplierSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        supplier = self.get_object()
        serializer = SupplierWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        supplier = services.update_supplier(supplier, dict(serializer.validated_data))
        return Response(SupplierSerializer(supplier).data)

    def set_active(self, instance: Supplier, *, is_active: bool) -> Supplier:
        return services.set_supplier_active(instance, is_active=is_active)
