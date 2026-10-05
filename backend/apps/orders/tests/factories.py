from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from rest_framework.test import APIClient

from apps.catalog.models import Product
from apps.catalog.tests.factories import make_product
from apps.customers.models import Customer, CustomerAddress
from apps.customers.tests.factories import make_address, make_customer
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user
from apps.inventory.models import Warehouse
from apps.inventory.tests.factories import make_warehouse
from apps.pricing.models import PriceList
from apps.pricing.tests.factories import make_price_list, set_price

ORDERS = "/api/v1/orders"


@dataclass
class Scenario:
    """Organização pronta para vender: cliente com endereço, depósito e dois produtos com preço
    (COLA a 3,50 e AGUA a 2,00 na tabela padrão)."""

    user: User
    customer: Customer
    address: CustomerAddress
    warehouse: Warehouse
    cola: Product
    water: Product
    price_list: PriceList
    client: APIClient = field(init=False)

    def __post_init__(self) -> None:
        self.client = authenticated_client(self.user)

    @property
    def organization_id(self) -> UUID:
        return self.user.organization_id  # type: ignore[return-value]

    def payload(self, **overrides: Any) -> dict[str, Any]:
        return {
            "customer_id": str(self.customer.id),
            "warehouse_id": str(self.warehouse.id),
            "lines": [
                {"product_id": str(self.cola.id), "quantity": 2},
                {"product_id": str(self.water.id), "quantity": 3},
            ],
            **overrides,
        }

    # `Any`: a resposta do cliente de teste (`.json()`, headers) não é tipada nos stubs.
    def place(self, payload: dict[str, Any] | None = None, *, key: Any = None) -> Any:
        return self.client.post(
            ORDERS,
            payload if payload is not None else self.payload(),
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(key or uuid4()),
        )

    def draft(self, **overrides: Any) -> Any:
        return self.client.post(f"{ORDERS}/drafts", self.payload(**overrides), format="json")


def make_scenario(role: Role = Role.SALES) -> Scenario:
    user = make_user(role=role)
    org = user.organization
    customer = make_customer(organization=org)
    address = make_address(customer, is_billing=True, is_default_shipping=True)
    price_list = make_price_list(user.organization_id)
    cola = make_product(organization=org, sku="COLA", name="Refrigerante Cola")
    water = make_product(organization=org, sku="AGUA", name="Água Mineral")
    set_price(price_list, cola, "3.50")
    set_price(price_list, water, "2.00")
    return Scenario(
        user=user,
        customer=customer,
        address=address,
        warehouse=make_warehouse(organization=org),
        cola=cola,
        water=water,
        price_list=price_list,
    )
