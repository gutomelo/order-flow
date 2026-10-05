from typing import Any, cast

import factory

from apps.identity.tests.factories import OrganizationFactory
from apps.suppliers.models import Supplier
from shared.testing.documents import generate_cnpj


class SupplierFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Supplier

    organization = factory.SubFactory(OrganizationFactory)
    legal_name = factory.Faker("company", locale="pt_BR")
    tax_id = factory.LazyFunction(generate_cnpj)


def make_supplier(**kwargs: Any) -> Supplier:
    return cast(Supplier, SupplierFactory(**kwargs))
