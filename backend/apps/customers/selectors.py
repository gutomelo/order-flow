"""Leituras públicas de clientes para outros módulos (ex.: orders, Phase 6)."""

from uuid import UUID

from apps.customers.models import Customer


def get_active_customer(organization_id: UUID, customer_id: UUID) -> Customer | None:
    """Cliente ativo da organização, ou None (regra CU5: inativo não recebe pedidos)."""
    return (
        Customer.objects.for_organization(organization_id)
        .filter(id=customer_id, is_active=True)
        .first()
    )
