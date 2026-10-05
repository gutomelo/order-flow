import pytest
from rest_framework.test import APIClient

from apps.catalog.tests.factories import make_product
from apps.customers.tests.factories import make_segment
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user
from apps.pricing.models import PriceList
from apps.pricing.tests.factories import make_price_list, set_price

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = "/api/v1/price-lists"


@pytest.fixture
def manager() -> User:
    return make_user(role=Role.MANAGER)


@pytest.fixture
def client(manager: User) -> APIClient:
    return authenticated_client(manager)


def test_creates_default_and_segment_lists_once_each(manager: User, client: APIClient) -> None:
    segment = make_segment(organization=manager.organization)

    default = client.post(URL, {"name": "Padrão"}, format="json")
    second_default = client.post(URL, {"name": "Outra padrão"}, format="json")
    by_segment = client.post(URL, {"name": "Atacado", "segment_id": str(segment.id)})
    second_segment = client.post(URL, {"name": "Atacado 2", "segment_id": str(segment.id)})

    assert default.status_code == 201
    assert default.json()["is_default"] is True
    assert by_segment.status_code == 201
    assert by_segment.json()["segment"]["id"] == str(segment.id)
    for response in (second_default, second_segment):
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "PRICE_LIST_ALREADY_EXISTS"


def test_names_are_unique_and_segments_must_be_active(manager: User, client: APIClient) -> None:
    make_price_list(manager.organization_id, name="Padrão")
    inactive = make_segment(organization=manager.organization, is_active=False)

    same_name = client.post(URL, {"name": "Padrão", "segment_id": None}, format="json")
    inactive_segment = client.post(URL, {"name": "Gov", "segment_id": str(inactive.id)})

    assert same_name.json()["error"]["code"] == "PRICE_LIST_NAME_ALREADY_IN_USE"
    assert inactive_segment.json()["error"]["code"] == "SEGMENT_NOT_AVAILABLE"


def test_items_are_added_searched_repriced_and_removed(manager: User, client: APIClient) -> None:
    price_list = make_price_list(manager.organization_id)
    cola = make_product(organization=manager.organization, sku="COLA", name="Cola")
    make_product(organization=manager.organization, sku="AGUA", name="Água")
    items = f"{URL}/{price_list.id}/items"

    created = client.post(items, {"product_id": str(cola.id), "unit_price": "3.5"})
    duplicated = client.post(items, {"product_id": str(cola.id), "unit_price": "4.00"})
    found = client.get(f"{items}?search=cola").json()["results"]
    repriced = client.patch(f"{items}/{created.json()['id']}", {"unit_price": "3.99"})
    removed = client.delete(f"{items}/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["unit_price"] == "3.50"
    assert duplicated.json()["error"]["code"] == "PRICE_ITEM_ALREADY_EXISTS"
    assert [i["product"]["sku"] for i in found] == ["COLA"]
    assert repriced.json()["unit_price"] == "3.99"
    assert removed.status_code == 204


@pytest.mark.parametrize("price", ["-1", "1.234", "abc"])
def test_rejects_invalid_prices(manager: User, client: APIClient, price: str) -> None:
    price_list = make_price_list(manager.organization_id)
    product = make_product(organization=manager.organization)

    response = client.post(
        f"{URL}/{price_list.id}/items", {"product_id": str(product.id), "unit_price": price}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_inactive_products_cannot_receive_a_price(manager: User, client: APIClient) -> None:
    price_list = make_price_list(manager.organization_id)
    product = make_product(organization=manager.organization, is_active=False)

    response = client.post(
        f"{URL}/{price_list.id}/items", {"product_id": str(product.id), "unit_price": "1"}
    )

    assert response.json()["error"]["code"] == "PRODUCT_NOT_AVAILABLE"


def test_deleting_a_list_removes_its_items(manager: User, client: APIClient) -> None:
    price_list = make_price_list(manager.organization_id)
    set_price(price_list, make_product(organization=manager.organization), "1.00")

    assert client.delete(f"{URL}/{price_list.id}").status_code == 204
    assert not PriceList.objects.filter(id=price_list.id).exists()


def test_lists_and_items_of_another_organization_are_not_found(client: APIClient) -> None:
    foreign = make_price_list(make_user().organization_id)

    assert client.get(f"{URL}/{foreign.id}").status_code == 404
    assert client.get(f"{URL}/{foreign.id}/items").status_code == 404
    assert client.delete(f"{URL}/{foreign.id}").status_code == 404


@pytest.mark.parametrize(
    ("role", "read", "manage"),
    [
        (Role.ADMIN, 200, 201),
        (Role.MANAGER, 200, 201),
        (Role.SALES, 200, 403),
        (Role.FINANCE, 200, 403),
        (Role.VIEWER, 200, 403),
        (Role.WAREHOUSE, 403, 403),
    ],
)
def test_permission_matrix(role: Role, read: int, manage: int) -> None:
    client = authenticated_client(make_user(role=role))

    assert client.get(URL).status_code == read
    assert client.post(URL, {"name": "Nova"}).status_code == manage
