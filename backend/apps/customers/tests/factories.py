from typing import Any, cast

import factory

from apps.customers.models import (
    BrazilianState,
    Customer,
    CustomerAddress,
    CustomerContact,
    CustomerSegment,
)
from apps.identity.tests.factories import OrganizationFactory
from shared.testing.documents import generate_cnpj


class SegmentFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = CustomerSegment

    organization = factory.SubFactory(OrganizationFactory)
    code = factory.Sequence(lambda n: f"SEG-{n:03d}")
    name = factory.Sequence(lambda n: f"Segmento {n}")


class CustomerFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Customer

    organization = factory.SubFactory(OrganizationFactory)
    legal_name = factory.Faker("company", locale="pt_BR")
    tax_id = factory.LazyFunction(generate_cnpj)


def make_segment(**kwargs: Any) -> CustomerSegment:
    return cast(CustomerSegment, SegmentFactory(**kwargs))


def make_customer(**kwargs: Any) -> Customer:
    return cast(Customer, CustomerFactory(**kwargs))


def make_address(customer: Customer, **kwargs: Any) -> CustomerAddress:
    """Endereço direto no banco (sem as regras de papel) — só para preparar cenários."""
    values: dict[str, Any] = {
        "label": "Matriz",
        "postal_code": "01310100",
        "street": "Avenida Paulista",
        "number": "1000",
        "district": "Bela Vista",
        "city": "São Paulo",
        "state": BrazilianState.SP,
        **kwargs,
    }
    return CustomerAddress.objects.create(
        organization_id=customer.organization_id, customer=customer, **values
    )


def make_contact(customer: Customer, **kwargs: Any) -> CustomerContact:
    values: dict[str, Any] = {"name": "Maria Souza", "email": "maria@example.com", **kwargs}
    return CustomerContact.objects.create(
        organization_id=customer.organization_id, customer=customer, **values
    )
