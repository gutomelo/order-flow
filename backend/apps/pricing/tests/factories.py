from decimal import Decimal
from typing import Any

from apps.catalog.models import Product
from apps.pricing.models import PriceList, PriceListItem


def make_price_list(organization_id: Any, *, name: str = "Padrão", **kwargs: Any) -> PriceList:
    return PriceList.objects.create(organization_id=organization_id, name=name, **kwargs)


def set_price(price_list: PriceList, product: Product, price: str) -> PriceListItem:
    return PriceListItem.objects.create(
        organization_id=price_list.organization_id,
        price_list=price_list,
        product=product,
        unit_price=Decimal(price),
    )
