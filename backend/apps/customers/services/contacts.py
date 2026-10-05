from dataclasses import dataclass, fields
from typing import Any

import structlog
from django.db import transaction

from apps.customers.exceptions import ContactChannelRequired
from apps.customers.models import Customer, CustomerContact
from apps.customers.services._roles import lock_customer, move_role, promote_oldest

# Contatos são dados pessoais (LGPD): os logs registram apenas IDs.
logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ContactData:
    name: str
    job_title: str = ""
    email: str = ""
    phone: str = ""


def _ensure_channel(contact: CustomerContact) -> None:
    if not contact.email and not contact.phone:  # CT1
        raise ContactChannelRequired(details={"field": "email"})


def add_contact(customer: Customer, data: ContactData) -> CustomerContact:
    contact = CustomerContact(
        organization_id=customer.organization_id,
        customer_id=customer.id,
        **{f.name: getattr(data, f.name).strip() for f in fields(ContactData)},
    )
    _ensure_channel(contact)
    with transaction.atomic():
        lock_customer(customer.id)
        # CT2: o primeiro contato é o principal.
        contact.is_primary = not CustomerContact.objects.filter(customer_id=customer.id).exists()
        contact.save()
    logger.info(
        "customers.contact.created", customer_id=str(customer.id), contact_id=str(contact.id)
    )
    return contact


def update_contact(contact: CustomerContact, changes: dict[str, Any]) -> CustomerContact:
    allowed = {f.name for f in fields(ContactData)}
    for name, value in changes.items():
        if name in allowed:
            setattr(contact, name, value.strip())
    _ensure_channel(contact)
    contact.save()
    return contact


def set_primary_contact(contact: CustomerContact) -> CustomerContact:
    with transaction.atomic():
        lock_customer(contact.customer_id)
        move_role(CustomerContact, contact.customer_id, contact.id, "is_primary")
    contact.refresh_from_db()
    return contact


def remove_contact(contact: CustomerContact) -> None:
    with transaction.atomic():
        lock_customer(contact.customer_id)
        current = CustomerContact.objects.filter(id=contact.id).first()
        if current is None:
            return
        was_primary = current.is_primary
        current.delete()
        if was_primary:
            promote_oldest(CustomerContact, contact.customer_id, "is_primary")
    logger.info(
        "customers.contact.removed",
        customer_id=str(contact.customer_id),
        contact_id=str(contact.id),
    )
