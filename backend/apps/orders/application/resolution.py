"""Resolve as referências do pedido nos módulos donos — sempre pelas interfaces públicas deles."""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from apps.catalog.selectors import get_sellable_products
from apps.customers.models import Customer, CustomerAddress
from apps.customers.selectors import (
    get_active_customer,
    get_customer_address,
    get_default_shipping_address,
)
from apps.inventory.application.queries import get_active_warehouse
from apps.inventory.models import Warehouse
from apps.orders.domain.exceptions import (
    AddressNotAvailable,
    AddressRequired,
    CustomerInactive,
    ProductUnavailable,
    WarehouseNotAvailable,
    WarehouseRequired,
)
from apps.orders.domain.lines import LineRequest, PricedLine
from apps.pricing.selectors import quote_prices


def active_customer(organization_id: UUID, customer_id: UUID) -> Customer:
    customer = get_active_customer(organization_id, customer_id)
    if customer is None:
        raise CustomerInactive(details={"field": "customer_id"})
    return customer


def chosen_address(
    organization_id: UUID, customer_id: UUID, address_id: UUID | None, *, required: bool
) -> CustomerAddress | None:
    """Endereço informado (precisa ser do cliente) ou, sem escolha, a entrega padrão."""
    if address_id is not None:
        address = get_customer_address(organization_id, customer_id, address_id)
        if address is None:
            raise AddressNotAvailable(details={"field": "shipping_address_id"})
        return address
    address = get_default_shipping_address(organization_id, customer_id)
    if address is None and required:
        raise AddressRequired(details={"field": "shipping_address_id"})
    return address


def chosen_warehouse(
    organization_id: UUID, warehouse_id: UUID | None, *, required: bool
) -> Warehouse | None:
    if warehouse_id is None:
        if required:
            raise WarehouseRequired(details={"field": "warehouse_id"})
        return None
    warehouse = get_active_warehouse(organization_id, warehouse_id)
    if warehouse is None:
        raise WarehouseNotAvailable(details={"field": "warehouse_id"})
    return warehouse


def price_lines(
    organization_id: UUID, customer: Customer, lines: Sequence[LineRequest]
) -> list[PricedLine]:
    """Produtos ativos + preço do cliente (pricing decide; orders só copia)."""
    if not lines:
        return []
    product_ids = [line.product_id for line in lines]
    products = {p.id: p for p in get_sellable_products(organization_id, product_ids)}
    missing = [str(pid) for pid in product_ids if pid not in products]
    if missing:
        raise ProductUnavailable(details={"product_ids": missing})
    quotes = quote_prices(organization_id, customer.segment_id, product_ids)
    return [
        PricedLine(
            product_id=line.product_id,
            sku=products[line.product_id].sku,
            product_name=products[line.product_id].name,
            quantity=line.quantity,
            unit_price=quotes[line.product_id].unit_price,
            price_source=quotes[line.product_id].source.value,
        )
        for line in lines
    ]


def address_snapshot(address: CustomerAddress) -> dict[str, Any]:
    """Cópia do endereço no pedido (AD4): editar ou remover o original não altera o pedido."""
    return {
        "address_id": str(address.id),
        "label": address.label,
        "postal_code": address.postal_code,
        "street": address.street,
        "number": address.number,
        "complement": address.complement,
        "district": address.district,
        "city": address.city,
        "state": address.state,
    }
