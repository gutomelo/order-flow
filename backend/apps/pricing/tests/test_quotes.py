from decimal import Decimal
from uuid import uuid4

import pytest

from apps.catalog.tests.factories import make_product
from apps.customers.tests.factories import make_segment
from apps.identity.tests.factories import make_organization
from apps.pricing.exceptions import PriceNotFound
from apps.pricing.selectors import PriceSource, quote_prices
from apps.pricing.tests.factories import make_price_list, set_price
from shared.domain.money import Money

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_segment_price_wins_and_default_is_the_fallback() -> None:
    org = make_organization()
    segment = make_segment(organization=org)
    cola, water = make_product(organization=org), make_product(organization=org)
    default = make_price_list(org.id)
    wholesale = make_price_list(org.id, name="Atacado", segment=segment)
    set_price(default, cola, "3.50")
    set_price(default, water, "2.00")
    set_price(wholesale, cola, "2.90")

    quotes = quote_prices(org.id, segment.id, [cola.id, water.id])

    assert quotes[cola.id].unit_price == Money(Decimal("2.90"))
    assert quotes[cola.id].source == PriceSource.SEGMENT
    assert quotes[water.id].unit_price == Money(Decimal("2.00"))
    assert quotes[water.id].source == PriceSource.DEFAULT


def test_customer_without_segment_uses_only_the_default_list() -> None:
    org = make_organization()
    segment = make_segment(organization=org)
    cola = make_product(organization=org)
    set_price(make_price_list(org.id, name="Atacado", segment=segment), cola, "2.90")
    set_price(make_price_list(org.id), cola, "3.50")

    assert quote_prices(org.id, None, [cola.id])[cola.id].unit_price == Money(Decimal("3.50"))


def test_product_without_price_cannot_be_sold() -> None:
    org = make_organization()
    priced, unpriced = make_product(organization=org), make_product(organization=org)
    set_price(make_price_list(org.id), priced, "1.00")

    with pytest.raises(PriceNotFound) as exc:
        quote_prices(org.id, None, [priced.id, unpriced.id])

    assert exc.value.details == {"product_ids": [str(unpriced.id)]}


def test_prices_of_another_organization_are_ignored() -> None:
    org, other = make_organization(), make_organization()
    product = make_product(organization=org)
    # Mesmo produto referenciado por uma tabela de outra organização (dado inconsistente).
    foreign = make_price_list(other.id)
    set_price(foreign, product, "0.01")

    with pytest.raises(PriceNotFound):
        quote_prices(org.id, None, [product.id, uuid4()])
