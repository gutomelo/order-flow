import random
import string
from typing import Any, cast

import factory

from apps.identity.tests.factories import OrganizationFactory
from apps.suppliers.models import Supplier

_FIRST = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_SECOND = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


def _digit(base: str, weights: tuple[int, ...]) -> str:
    remainder = sum((ord(c) - 48) * w for c, w in zip(base, weights, strict=True)) % 11
    return "0" if remainder < 2 else str(11 - remainder)


def generate_cnpj(alphanumeric: bool = False) -> str:
    """CNPJ válido aleatório (numérico ou alfanumérico) para testes."""
    alphabet = string.digits + (string.ascii_uppercase if alphanumeric else "")
    base = "".join(random.choices(alphabet, k=12))  # noqa: S311 (dado de teste)
    first = _digit(base, _FIRST)
    return base + first + _digit(base + first, _SECOND)


class SupplierFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Supplier

    organization = factory.SubFactory(OrganizationFactory)
    legal_name = factory.Faker("company", locale="pt_BR")
    tax_id = factory.LazyFunction(generate_cnpj)


def make_supplier(**kwargs: Any) -> Supplier:
    return cast(Supplier, SupplierFactory(**kwargs))
