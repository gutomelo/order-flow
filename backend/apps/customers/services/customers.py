from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction

from apps.customers.exceptions import InvalidTaxId, SegmentNotAvailable, TaxIdAlreadyInUse
from apps.customers.models import Customer, CustomerSegment
from shared.domain.documents import is_valid_cnpj, normalize_cnpj

logger = structlog.get_logger(__name__)

_TEXT_FIELDS = ("legal_name", "trade_name", "email", "phone")


@dataclass(frozen=True)
class CustomerData:
    legal_name: str
    tax_id: str
    trade_name: str = ""
    email: str = ""
    phone: str = ""
    segment_id: UUID | None = None


def _validated_tax_id(raw: str) -> str:
    if not is_valid_cnpj(raw):  # CU1
        raise InvalidTaxId(details={"field": "tax_id"})
    return normalize_cnpj(raw)


def _lock_available_segment(organization_id: UUID, segment_id: UUID) -> CustomerSegment:
    """CU4/SG3 com lock: a inativação do segmento espera este cadastro terminar (e vice-versa)."""
    segment = (
        CustomerSegment.objects.for_organization(organization_id)
        .select_for_update()
        .filter(id=segment_id)
        .first()
    )
    if segment is None or not segment.is_active:
        raise SegmentNotAvailable(details={"field": "segment_id"})
    return segment


def _save(customer: Customer) -> Customer:
    try:
        with transaction.atomic():
            customer.save()
    except IntegrityError as exc:
        # CU2: UNIQUE (organization_id, tax_id) — inclusive em cadastros concorrentes.
        raise TaxIdAlreadyInUse(details={"field": "tax_id"}) from exc
    return customer


def create_customer(organization_id: UUID, data: CustomerData) -> Customer:
    customer = Customer(
        organization_id=organization_id,
        legal_name=data.legal_name.strip(),
        trade_name=data.trade_name.strip(),
        tax_id=_validated_tax_id(data.tax_id),
        email=data.email,
        phone=data.phone.strip(),
    )
    with transaction.atomic():
        if data.segment_id is not None:
            customer.segment = _lock_available_segment(organization_id, data.segment_id)
        _save(customer)
    logger.info("customers.customer.created", customer_id=str(customer.id))
    return customer


def update_customer(customer: Customer, changes: dict[str, Any]) -> Customer:
    with transaction.atomic():
        customer = Customer.objects.select_for_update(of=("self",)).get(id=customer.id)
        for name in _TEXT_FIELDS:
            if name in changes:
                setattr(customer, name, changes[name].strip())
        if "tax_id" in changes:
            customer.tax_id = _validated_tax_id(changes["tax_id"])
        if "segment_id" in changes and changes["segment_id"] != customer.segment_id:
            segment_id: UUID | None = changes["segment_id"]
            customer.segment = (
                None
                if segment_id is None
                else _lock_available_segment(customer.organization_id, segment_id)
            )
        _save(customer)
    return customer


def set_customer_active(customer: Customer, *, is_active: bool) -> Customer:
    with transaction.atomic():
        customer = Customer.objects.select_for_update(of=("self",)).get(id=customer.id)
        if customer.is_active == is_active:
            return customer
        if is_active and customer.segment_id is not None:
            # CU4: o segmento pode ter sido inativado enquanto o cliente estava inativo.
            _lock_available_segment(customer.organization_id, customer.segment_id)
        customer.is_active = is_active
        customer.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "customers.customer.activated" if is_active else "customers.customer.deactivated",
        customer_id=str(customer.id),
    )
    return customer
