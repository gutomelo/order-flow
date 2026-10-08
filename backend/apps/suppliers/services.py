"""Operações de escrita de fornecedores (módulo simples: regras cabem em um serviço)."""

from dataclasses import dataclass, fields
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction

from apps.suppliers.exceptions import InvalidTaxId, TaxIdAlreadyInUse
from apps.suppliers.models import Supplier
from shared.domain.documents import is_valid_cnpj, normalize_cnpj

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SupplierData:
    legal_name: str
    tax_id: str
    trade_name: str = ""
    email: str = ""
    phone: str = ""


def _validated_tax_id(raw: str) -> str:
    if not is_valid_cnpj(raw):  # S1
        raise InvalidTaxId(details={"field": "tax_id"})
    return normalize_cnpj(raw)


def _save(supplier: Supplier) -> Supplier:
    try:
        with transaction.atomic():
            supplier.save()
    except IntegrityError as exc:
        # S2: UNIQUE (organization_id, tax_id) — inclusive em criações concorrentes.
        raise TaxIdAlreadyInUse() from exc
    return supplier


def create_supplier(organization_id: UUID, data: SupplierData) -> Supplier:
    supplier = Supplier(
        organization_id=organization_id,
        legal_name=data.legal_name.strip(),
        trade_name=data.trade_name.strip(),
        tax_id=_validated_tax_id(data.tax_id),
        email=data.email,
        phone=data.phone.strip(),
    )
    _save(supplier)
    logger.info("suppliers.supplier.created", supplier_id=str(supplier.id))
    return supplier


def update_supplier(supplier: Supplier, changes: dict[str, str]) -> Supplier:
    allowed = {field.name for field in fields(SupplierData)}
    for name, value in changes.items():
        if name not in allowed:
            continue
        setattr(supplier, name, _validated_tax_id(value) if name == "tax_id" else value.strip())
    return _save(supplier)


def set_supplier_active(supplier: Supplier, *, is_active: bool) -> Supplier:
    # S3: inativação mantém as referências (produtos continuam apontando para o fornecedor).
    if supplier.is_active != is_active:
        supplier.is_active = is_active
        supplier.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "suppliers.supplier.activated" if is_active else "suppliers.supplier.deactivated",
            supplier_id=str(supplier.id),
        )
    return supplier
