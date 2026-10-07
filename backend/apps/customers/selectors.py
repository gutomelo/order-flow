"""Leituras públicas de clientes para outros módulos (ex.: orders)."""

from dataclasses import dataclass
from uuid import UUID

from apps.customers.models import Customer, CustomerAddress, CustomerContact


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


@dataclass(frozen=True)
class NotificationRecipient:
    email: str
    name: str  # para a saudação: nome do contato, ou do cliente


def get_notification_recipient(
    organization_id: UUID, customer_id: UUID
) -> NotificationRecipient | None:
    """Quem recebe os avisos do pedido: o contato principal com e-mail; sem ele, o e-mail do
    cadastro do cliente; sem nenhum, `None` (a notificação fica registrada sem destinatário)."""
    customer = Customer.objects.for_organization(organization_id).filter(id=customer_id).first()
    if customer is None:
        return None
    primary = (
        CustomerContact.objects.for_organization(organization_id)
        .filter(customer=customer, is_primary=True)
        .exclude(email="")
        .first()
    )
    if primary is not None:
        return NotificationRecipient(primary.email, primary.name)
    if customer.email:
        return NotificationRecipient(customer.email, customer.display_name)
    return None
