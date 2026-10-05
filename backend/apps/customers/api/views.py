from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.customers.api.serializers import (
    AddressSerializer,
    AddressWriteSerializer,
    ContactSerializer,
    ContactWriteSerializer,
    CustomerSerializer,
    CustomerWriteSerializer,
    SegmentCreateSerializer,
    SegmentSerializer,
    SegmentUpdateSerializer,
)
from apps.customers.models import Customer, CustomerAddress, CustomerContact, CustomerSegment
from apps.customers.services import addresses, contacts, customers, segments
from apps.identity.domain.permissions import Permission
from shared.api.activation import ActivationActionsMixin
from shared.permissions import HasPermission, HasReadWritePermission
from shared.tenancy.api import TenantScopedQuerysetMixin

if TYPE_CHECKING:
    from rest_framework.permissions import _SupportsHasPermission

_READ_UPDATE = HasReadWritePermission(
    read=Permission.CUSTOMERS_READ, write=Permission.CUSTOMERS_UPDATE
)


class SegmentViewSet(
    ActivationActionsMixin,
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[CustomerSegment],
):
    queryset = CustomerSegment.objects.annotate(
        active_customers=Count("customers", filter=Q(customers__is_active=True))
    )
    serializer_class = SegmentSerializer
    permission_classes = (
        IsAuthenticated,
        HasReadWritePermission(
            read=Permission.CUSTOMERS_READ, write=Permission.CUSTOMERS_MANAGE_SEGMENTS
        ),
    )
    http_method_names = ("get", "post", "patch", "head", "options")
    filterset_fields = ("is_active",)
    search_fields = ("code", "name")
    ordering_fields = ("code", "name", "created_at")
    ordering = ("name",)

    @extend_schema(request=SegmentCreateSerializer, responses={201: SegmentSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = SegmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        segment = segments.create_segment(self.organization_id, **serializer.validated_data)
        return Response(SegmentSerializer(segment).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=SegmentUpdateSerializer, responses=SegmentSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        segment = self.get_object()
        serializer = SegmentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        segment = segments.update_segment(segment, **serializer.validated_data)
        return Response(SegmentSerializer(segment).data)

    def set_active(self, instance: CustomerSegment, *, is_active: bool) -> CustomerSegment:
        return segments.set_segment_active(instance, is_active=is_active)


class CustomerViewSet(
    ActivationActionsMixin,
    TenantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet[Customer],
):
    queryset = Customer.objects.select_related("segment")
    serializer_class = CustomerSerializer
    permission_classes = (IsAuthenticated, _READ_UPDATE)
    http_method_names = ("get", "post", "patch", "head", "options")
    filterset_fields = ("is_active", "segment")
    search_fields = ("legal_name", "trade_name", "tax_id", "email")
    ordering_fields = ("legal_name", "trade_name", "created_at")
    ordering = ("legal_name",)

    def get_permissions(self) -> Sequence["_SupportsHasPermission"]:
        # Criar e editar são permissões distintas na matriz (security.md).
        if self.action == "create":
            return [IsAuthenticated(), HasPermission(Permission.CUSTOMERS_CREATE)()]
        return super().get_permissions()

    @extend_schema(request=CustomerWriteSerializer, responses={201: CustomerSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CustomerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = customers.create_customer(
            self.organization_id, customers.CustomerData(**serializer.validated_data)
        )
        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=CustomerWriteSerializer, responses=CustomerSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        customer = self.get_object()
        serializer = CustomerWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        customer = customers.update_customer(customer, dict(serializer.validated_data))
        return Response(CustomerSerializer(customer).data)

    def set_active(self, instance: Customer, *, is_active: bool) -> Customer:
        return customers.set_customer_active(instance, is_active=is_active)


class _CustomerChildViewSet(TenantScopedQuerysetMixin):
    """Recursos de um cliente (`/customers/{customer_pk}/...`).

    O queryset é filtrado pela organização **e** pelo cliente da URL: o endereço de outro cliente
    responde 404 mesmo que o ID exista (anti-IDOR).
    """

    permission_classes = (IsAuthenticated, _READ_UPDATE)
    pagination_class = None
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_customer(self) -> Customer:
        return get_object_or_404(
            Customer.objects.for_organization(self.organization_id), id=self.kwargs["customer_pk"]
        )

    def get_queryset(self) -> QuerySet[Any]:
        return super().get_queryset().filter(customer_id=self.kwargs["customer_pk"])

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        self.get_customer()  # cliente inexistente → 404, não lista vazia
        return Response(self.get_serializer(self.get_queryset(), many=True).data)


class AddressViewSet(_CustomerChildViewSet, viewsets.GenericViewSet[CustomerAddress]):
    queryset = CustomerAddress.objects.all()
    serializer_class = AddressSerializer

    @extend_schema(request=AddressWriteSerializer, responses={201: AddressSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        customer = self.get_customer()
        serializer = AddressWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = addresses.add_address(
            customer, addresses.AddressData(**serializer.validated_data)
        )
        return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=AddressWriteSerializer, responses=AddressSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        address = self.get_object()
        serializer = AddressWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        address = addresses.update_address(address, dict(serializer.validated_data))
        return Response(AddressSerializer(address).data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        addresses.remove_address(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=AddressSerializer)
    @action(detail=True, methods=["post"], url_path="set-billing")
    def set_billing(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        address = addresses.set_address_role(self.get_object(), "is_billing")
        return Response(AddressSerializer(address).data)

    @extend_schema(request=None, responses=AddressSerializer)
    @action(detail=True, methods=["post"], url_path="set-default-shipping")
    def set_default_shipping(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        address = addresses.set_address_role(self.get_object(), "is_default_shipping")
        return Response(AddressSerializer(address).data)


class ContactViewSet(_CustomerChildViewSet, viewsets.GenericViewSet[CustomerContact]):
    queryset = CustomerContact.objects.all()
    serializer_class = ContactSerializer

    @extend_schema(request=ContactWriteSerializer, responses={201: ContactSerializer})
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        customer = self.get_customer()
        serializer = ContactWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = contacts.add_contact(customer, contacts.ContactData(**serializer.validated_data))
        return Response(ContactSerializer(contact).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=ContactWriteSerializer, responses=ContactSerializer)
    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        contact = self.get_object()
        serializer = ContactWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        contact = contacts.update_contact(contact, dict(serializer.validated_data))
        return Response(ContactSerializer(contact).data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        contacts.remove_contact(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=ContactSerializer)
    @action(detail=True, methods=["post"], url_path="set-primary")
    def set_primary(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        contact = contacts.set_primary_contact(self.get_object())
        return Response(ContactSerializer(contact).data)
