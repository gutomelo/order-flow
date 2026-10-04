import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category
from apps.catalog.selectors import descendant_ids
from apps.catalog.tests.factories import make_category, make_product
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def manager() -> User:
    return make_user(role=Role.MANAGER)


@pytest.fixture
def client(manager: User) -> APIClient:
    return authenticated_client(manager)


def _create(client: APIClient, name: str, parent: Category | None = None):  # type: ignore[no-untyped-def]
    payload = {"name": name, "parent_id": str(parent.id) if parent else None}
    return client.post("/api/v1/categories", payload, format="json")


def test_tree_is_listed_parent_first_with_paths(manager: User, client: APIClient) -> None:
    drinks = make_category(organization=manager.organization, name="Bebidas")
    make_category(parent=drinks, name="Sucos")
    make_category(parent=drinks, name="Refrigerantes")
    make_category(organization=manager.organization, name="Alimentos")
    make_category(name="De outra organização")

    response = client.get("/api/v1/categories")

    assert [c["path"] for c in response.json()] == [
        "Alimentos",
        "Bebidas",
        "Bebidas › Refrigerantes",  # noqa: RUF001
        "Bebidas › Sucos",  # noqa: RUF001
    ]


def test_depth_is_limited_to_three_levels(client: APIClient) -> None:
    level1 = Category.objects.get(id=_create(client, "Bebidas").json()["id"])
    level2 = Category.objects.get(id=_create(client, "Refrigerantes", level1).json()["id"])
    level3 = _create(client, "Lata", level2)

    level4 = _create(client, "Promoção", Category.objects.get(id=level3.json()["id"]))

    assert level3.json()["depth"] == 3
    assert level4.status_code == 422
    assert level4.json()["error"]["code"] == "CATEGORY_DEPTH_EXCEEDED"


def test_sibling_names_are_unique_ignoring_case_including_roots(
    manager: User, client: APIClient
) -> None:
    drinks = make_category(organization=manager.organization, name="Bebidas")
    make_category(parent=drinks, name="Lata")

    duplicated_root = _create(client, "BEBIDAS")
    duplicated_child = _create(client, "lata", drinks)
    same_name_elsewhere = _create(client, "Lata")

    assert duplicated_root.status_code == 409
    assert duplicated_child.json()["error"]["code"] == "CATEGORY_NAME_ALREADY_IN_USE"
    assert same_name_elsewhere.status_code == 201


def test_moving_a_category_moves_its_subtree(manager: User, client: APIClient) -> None:
    drinks = make_category(organization=manager.organization, name="Bebidas")
    sodas = make_category(parent=drinks, name="Refrigerantes")
    cans = make_category(parent=sodas, name="Lata")

    response = client.patch(f"/api/v1/categories/{sodas.id}", {"parent_id": None}, format="json")

    assert response.status_code == 200
    cans.refresh_from_db()
    sodas.refresh_from_db()
    assert (sodas.depth, cans.depth) == (1, 2)


def test_cannot_move_category_into_its_own_subtree(manager: User, client: APIClient) -> None:
    drinks = make_category(organization=manager.organization)
    sodas = make_category(parent=drinks)

    into_child = client.patch(f"/api/v1/categories/{drinks.id}", {"parent_id": str(sodas.id)})
    into_itself = client.patch(f"/api/v1/categories/{drinks.id}", {"parent_id": str(drinks.id)})

    assert into_child.json()["error"]["code"] == "CATEGORY_CYCLE"
    assert into_itself.json()["error"]["code"] == "CATEGORY_CYCLE"


def test_cannot_move_a_subtree_beyond_three_levels(manager: User, client: APIClient) -> None:
    deep_parent = make_category(parent=make_category(organization=manager.organization))
    subtree_root = make_category(organization=manager.organization)
    make_category(parent=subtree_root)  # subárvore de 2 níveis

    response = client.patch(
        f"/api/v1/categories/{subtree_root.id}", {"parent_id": str(deep_parent.id)}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_DEPTH_EXCEEDED"


def test_category_with_active_children_cannot_be_deactivated(
    manager: User, client: APIClient
) -> None:
    drinks = make_category(organization=manager.organization)
    child = make_category(parent=drinks)

    blocked = client.post(f"/api/v1/categories/{drinks.id}/deactivate")
    client.post(f"/api/v1/categories/{child.id}/deactivate")
    allowed = client.post(f"/api/v1/categories/{drinks.id}/deactivate")

    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "CATEGORY_HAS_ACTIVE_CHILDREN"
    assert allowed.json()["is_active"] is False


def test_child_cannot_be_activated_under_inactive_parent(manager: User, client: APIClient) -> None:
    parent = make_category(organization=manager.organization, is_active=False)
    child = make_category(parent=parent, is_active=False)

    response = client.post(f"/api/v1/categories/{child.id}/activate")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PARENT_CATEGORY_INACTIVE"


def test_deactivating_a_category_keeps_its_products_active(
    manager: User, client: APIClient
) -> None:
    category = make_category(organization=manager.organization)
    product = make_product(organization=manager.organization, category=category)

    client.post(f"/api/v1/categories/{category.id}/deactivate")

    product.refresh_from_db()
    assert product.is_active is True


def test_parent_from_another_organization_is_rejected(client: APIClient) -> None:
    foreign = make_category()

    response = _create(client, "Infiltrada", foreign)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATEGORY_NOT_AVAILABLE"


def test_only_managers_can_change_categories() -> None:
    client = authenticated_client(make_user(role=Role.SALES))

    assert client.get("/api/v1/categories").status_code == 200
    assert _create(client, "X").status_code == 403


def test_descendant_lookup_terminates_even_if_a_cycle_reaches_the_database(manager: User) -> None:
    # Ciclo gravado à revelia das regras (ex.: dado legado): a leitura não pode travar.
    a = make_category(organization=manager.organization, name="A")
    b = make_category(parent=a, name="B")
    Category.objects.filter(id=a.id).update(parent=b, depth=3)

    assert descendant_ids(a.organization_id, a.id) == {a.id, b.id}
