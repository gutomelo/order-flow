from typing import Any, cast

import factory

from apps.catalog.tests.factories import make_product
from apps.identity.tests.factories import OrganizationFactory
from apps.inventory.models import StockItem, Warehouse


class WarehouseFactory(factory.django.DjangoModelFactory):  # type: ignore[type-arg]
    class Meta:
        model = Warehouse

    organization = factory.SubFactory(OrganizationFactory)
    code = factory.Sequence(lambda n: f"WH-{n:03d}")
    name = factory.Sequence(lambda n: f"Depósito {n}")


def make_warehouse(**kwargs: Any) -> Warehouse:
    return cast(Warehouse, WarehouseFactory(**kwargs))


def make_stock_item(
    *, warehouse: Warehouse | None = None, on_hand: int = 0, reserved: int = 0, **kwargs: Any
) -> StockItem:
    """Saldo inicial direto no banco — apenas para preparar cenários de teste.

    Em produção o saldo só muda pelo ledger (que também grava o movimento).
    """
    warehouse = warehouse or make_warehouse()
    product = kwargs.pop("product", None) or make_product(organization=warehouse.organization)
    item = StockItem.objects.create(
        organization=warehouse.organization,
        warehouse=warehouse,
        product=product,
        on_hand=on_hand,
        reserved=reserved,
        **kwargs,
    )
    item.refresh_from_db()  # `available` é calculado pelo banco
    return item
