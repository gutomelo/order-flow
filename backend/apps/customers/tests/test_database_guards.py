"""O banco protege as invariantes de clientes mesmo contra código que contorne os serviços."""

import pytest
from django.db import IntegrityError, transaction

from apps.customers.tests.factories import make_address, make_contact, make_customer

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.mark.parametrize("role", ["is_billing", "is_default_shipping"])
def test_at_most_one_address_per_role(role: str) -> None:  # AD2
    customer = make_customer()
    make_address(customer, **{role: True})

    with pytest.raises(IntegrityError), transaction.atomic():
        make_address(customer, **{role: True})


def test_roles_are_per_customer() -> None:
    first, second = make_customer(), make_customer()

    make_address(first, is_billing=True)
    make_address(second, is_billing=True)  # não conflita


@pytest.mark.parametrize(("field", "value"), [("postal_code", "0131010"), ("state", "XX")])
def test_address_format_is_enforced(field: str, value: str) -> None:  # AD1
    with pytest.raises(IntegrityError), transaction.atomic():
        make_address(make_customer(), **{field: value})


def test_at_most_one_primary_contact() -> None:  # CT2
    customer = make_customer()
    make_contact(customer, is_primary=True)

    with pytest.raises(IntegrityError), transaction.atomic():
        make_contact(customer, is_primary=True)


def test_contact_needs_a_channel() -> None:  # CT1
    with pytest.raises(IntegrityError), transaction.atomic():
        make_contact(make_customer(), email="", phone="")
