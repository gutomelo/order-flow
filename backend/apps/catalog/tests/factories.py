from typing import Any, cast

import factory

from apps.catalog.models import Category, Product
from apps.identity.tests.factories import OrganizationFactory


class CategoryFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Category

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Categoria {n}")
    depth = factory.LazyAttribute(lambda obj: obj.parent.depth + 1 if obj.parent else 1)
    parent = None


class ProductFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Product

    organization = factory.SubFactory(OrganizationFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    name = factory.Sequence(lambda n: f"Produto {n}")


def make_category(**kwargs: Any) -> Category:
    if "parent" in kwargs and kwargs["parent"] is not None:
        kwargs.setdefault("organization", kwargs["parent"].organization)
    return cast(Category, CategoryFactory(**kwargs))


def make_product(**kwargs: Any) -> Product:
    return cast(Product, ProductFactory(**kwargs))
