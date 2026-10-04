from typing import Any, cast
from uuid import UUID

from django.db.models import QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.catalog import services
from apps.catalog.api.serializers import (
    CategorySerializer,
    CategoryWriteSerializer,
    ProductCreateSerializer,
    ProductSerializer,
    ProductUpdateSerializer,
)
from apps.catalog.models import Category, Product
from apps.catalog.selectors import category_tree, descendant_ids
from apps.identity.domain.permissions import Permission
from shared.api.activation import ActivationActionsMixin
from shared.permissions import HasReadWritePermission
from shared.tenancy.api import TenantScopedQuerysetMixin

CATALOG_PERMISSIONS = HasReadWritePermission(
    read=Permission.CATALOG_READ, write=Permission.CATALOG_MANAGE
)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "category",
                OpenApiTypes.UUID,
                description="Filtra pela categoria e todas as suas subcategorias.",
            ),
            OpenApiParameter("supplier", OpenApiTypes.UUID, description="Fornecedor padrão."),
        ]
    )
)
class ProductViewSet(
    ActivationActionsMixin,
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Product],
):
    queryset = Product.objects.select_related(
        "category__parent__parent", "default_supplier"
    )  # caminho da categoria (até 3 níveis) e fornecedor sem N+1
    serializer_class = ProductSerializer
    permission_classes = (IsAuthenticated, CATALOG_PERMISSIONS)
    http_method_names = ("get", "post", "patch", "head", "options")
    filterset_fields = ("is_active", "unit")
    search_fields = ("name", "sku", "barcode")
    ordering_fields = ("name", "sku", "created_at", "updated_at")
    ordering = ("name",)

    def get_queryset(self) -> QuerySet[Product]:
        queryset: QuerySet[Product] = super().get_queryset()
        params = self.request.query_params
        if category := params.get("category"):
            queryset = queryset.filter(
                category_id__in=descendant_ids(
                    self.organization_id, self._uuid(category, "category")
                )
            )
        if supplier := params.get("supplier"):
            queryset = queryset.filter(default_supplier_id=self._uuid(supplier, "supplier"))
        return queryset

    @staticmethod
    def _uuid(value: str, field: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as exc:
            raise ValidationError({field: ["Identificador inválido."]}) from exc

    @extend_schema(request=ProductCreateSerializer, responses={201: ProductSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = services.create_product(
            self.organization_id, services.ProductData(**serializer.validated_data)
        )
        return Response(
            ProductSerializer(self.get_queryset().get(pk=product.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ProductUpdateSerializer, responses=ProductSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        product = self.get_object()
        serializer = ProductUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_product(product, dict(serializer.validated_data))
        return Response(ProductSerializer(self.get_queryset().get(pk=product.pk)).data)

    def set_active(self, instance: Product, *, is_active: bool) -> Product:
        services.set_product_active(instance, is_active=is_active)
        return self.get_queryset().get(pk=instance.pk)


class CategoryViewSet(
    ActivationActionsMixin,
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Category],
):
    """Árvore inteira em uma resposta (sem paginação): limitada a 3 níveis por organização."""

    queryset = Category.objects.select_related("parent__parent")
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated, CATALOG_PERMISSIONS)
    http_method_names = ("get", "post", "patch", "head", "options")
    pagination_class = None

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        nodes = category_tree(self.organization_id)
        if (active := request.query_params.get("is_active")) is not None:
            wanted = active.lower() == "true"
            nodes = [node for node in nodes if node.category.is_active is wanted]
        paths = {node.category.id: node.path for node in nodes}
        serializer = CategorySerializer(
            [node.category for node in nodes], many=True, context={"paths": paths}
        )
        return Response(serializer.data)

    @extend_schema(request=CategoryWriteSerializer, responses={201: CategorySerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = services.create_category(
            self.organization_id,
            name=serializer.validated_data["name"],
            parent_id=serializer.validated_data.get("parent_id"),
        )
        return Response(
            CategorySerializer(self.get_queryset().get(pk=category.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=CategoryWriteSerializer, responses=CategorySerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        category = self.get_object()
        serializer = CategoryWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes: dict[str, Any] = {}
        if "name" in serializer.validated_data:
            changes["name"] = serializer.validated_data["name"]
        if "parent_id" in serializer.validated_data:
            changes["parent_id"] = serializer.validated_data["parent_id"]
        services.update_category(category, **changes)
        return Response(CategorySerializer(self.get_queryset().get(pk=category.pk)).data)

    def set_active(self, instance: Category, *, is_active: bool) -> Category:
        services.set_category_active(instance, is_active=is_active)
        return cast(Category, self.get_queryset().get(pk=instance.pk))
