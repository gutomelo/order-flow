"""Leituras públicas de clientes para outros módulos (ex.: orders)."""

from uuid import UUID

from apps.customers.models import Customer, CustomerAddress


def get_active_customer(organization_id: UUID, customer_id: UUID) -> Customer | None:
    """Cliente ativo da organização, ou None (regra CU5: inativo não recebe pedidos)."""
    return (
        Customer.objects.for_organization(organization_id)
        .select_related("segment")
        .filter(id=customer_id, is_active=True)
        .first()
    )


def get_customer_address(
    organization_id: UUID, customer_id: UUID, address_id: UUID
) -> CustomerAddress | None:
    """Endereço **deste** cliente (um ID de endereço de outro cliente não serve)."""
    return (
        CustomerAddress.objects.for_organization(organization_id)
        .filter(id=address_id, customer_id=customer_id)
        .first()
    )


def get_default_shipping_address(
    organization_id: UUID, customer_id: UUID
) -> CustomerAddress | None:
    return (
        CustomerAddress.objects.for_organization(organization_id)
        .filter(customer_id=customer_id, is_default_shipping=True)
        .first()
    )
