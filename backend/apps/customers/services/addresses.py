import re
from dataclasses import dataclass, fields
from typing import Any, Literal

import structlog
from django.db import transaction

from apps.customers.exceptions import InvalidPostalCode
from apps.customers.models import Customer, CustomerAddress
from apps.customers.services._roles import lock_customer, move_role, promote_oldest

logger = structlog.get_logger(__name__)

AddressRole = Literal["is_billing", "is_default_shipping"]
ROLES: tuple[AddressRole, ...] = ("is_billing", "is_default_shipping")


@dataclass(frozen=True)
class AddressData:
    label: str
    postal_code: str
    street: str
    number: str
    district: str
    city: str
    state: str
    complement: str = ""


def normalize_postal_code(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 8:  # AD1
        raise InvalidPostalCode(details={"field": "postal_code"})
    return digits


def _clean(name: str, value: str) -> str:
    return normalize_postal_code(value) if name == "postal_code" else value.strip()


def add_address(customer: Customer, data: AddressData) -> CustomerAddress:
    values = {f.name: _clean(f.name, getattr(data, f.name)) for f in fields(AddressData)}
    with transaction.atomic():
        lock_customer(customer.id)
        # AD3: o primeiro endereço assume os dois papéis.
        first = not CustomerAddress.objects.filter(customer_id=customer.id).exists()
        address = CustomerAddress.objects.create(
            organization_id=customer.organization_id,
            customer_id=customer.id,
            is_billing=first,
            is_default_shipping=first,
            **values,
        )
    logger.info(
        "customers.address.created", customer_id=str(customer.id), address_id=str(address.id)
    )
    return address


def update_address(address: CustomerAddress, changes: dict[str, Any]) -> CustomerAddress:
    allowed = {f.name for f in fields(AddressData)}
    for name, value in changes.items():
        if name in allowed:
            setattr(address, name, _clean(name, value))
    address.save()
    return address


def set_address_role(address: CustomerAddress, role: AddressRole) -> CustomerAddress:
    with transaction.atomic():
        lock_customer(address.customer_id)
        move_role(CustomerAddress, address.customer_id, address.id, role)
    address.refresh_from_db()
    return address


def remove_address(address: CustomerAddress) -> None:
    with transaction.atomic():
        lock_customer(address.customer_id)
        # Relê após o lock: outra requisição pode ter movido os papéis ou removido o endereço.
        current = CustomerAddress.objects.filter(id=address.id).first()
        if current is None:
            return
        held = [role for role in ROLES if getattr(current, role)]
        current.delete()
        for role in held:  # AD3: o papel passa para o endereço mais antigo restante
            promote_oldest(CustomerAddress, address.customer_id, role)
    logger.info(
        "customers.address.removed",
        customer_id=str(address.customer_id),
        address_id=str(address.id),
    )
