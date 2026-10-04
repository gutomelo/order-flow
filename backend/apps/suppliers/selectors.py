"""Leituras públicas de fornecedores para outros módulos (ex.: catalog)."""

from uuid import UUID

from apps.suppliers.models import Supplier


def get_active_supplier(organization_id: UUID, supplier_id: UUID) -> Supplier | None:
    """Fornecedor ativo da organização, ou None (regra S4: inativo não é atribuível)."""
    return (
        Supplier.objects.for_organization(organization_id)
        .filter(id=supplier_id, is_active=True)
        .first()
    )
