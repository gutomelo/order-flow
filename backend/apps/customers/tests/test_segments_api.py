import pytest

from apps.customers.models import CustomerSegment
from apps.customers.tests.factories import make_customer, make_segment
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

URL = "/api/v1/customer-segments"


@pytest.fixture
def manager() -> User:
    return make_user(role=Role.MANAGER)


def test_creates_segment_with_normalized_code(manager: User) -> None:
    response = authenticated_client(manager).post(
        URL, {"code": " atacado-sp ", "name": "Atacado SP", "description": "Revendas paulistas"}
    )

    assert response.status_code == 201
    assert response.json()["code"] == "ATACADO-SP"
    assert response.json()["active_customers"] == 0


@pytest.mark.parametrize("code", ["A", "com espaço", "ÇÃO", "PONTO.FINAL"])
def test_rejects_invalid_codes(manager: User, code: str) -> None:
    response = authenticated_client(manager).post(URL, {"code": code, "name": "N"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_SEGMENT_CODE"


def test_code_is_unique_per_organization(manager: User) -> None:
    make_segment(organization=manager.organization, code="VAREJO")
    make_segment(code="GOVERNO")  # outra organização
    client = authenticated_client(manager)

    assert client.post(URL, {"code": "varejo", "name": "N"}).status_code == 409
    assert client.post(URL, {"code": "GOVERNO", "name": "N"}).status_code == 201


def test_code_is_immutable(manager: User) -> None:
    segment = make_segment(organization=manager.organization, code="VAREJO")

    response = authenticated_client(manager).patch(
        f"{URL}/{segment.id}", {"code": "OUTRO", "name": "Varejo nacional"}
    )

    assert response.status_code == 200
    assert response.json()["code"] == "VAREJO"
    assert response.json()["name"] == "Varejo nacional"


def test_list_counts_only_active_customers(manager: User) -> None:
    segment = make_segment(organization=manager.organization)
    make_customer(organization=manager.organization, segment=segment)
    make_customer(organization=manager.organization, segment=segment, is_active=False)
    make_segment()  # outra organização

    results = authenticated_client(manager).get(URL).json()["results"]

    assert [(s["id"], s["active_customers"]) for s in results] == [(str(segment.id), 1)]


def test_segment_with_active_customers_cannot_be_deactivated(manager: User) -> None:
    segment = make_segment(organization=manager.organization)
    make_customer(organization=manager.organization, segment=segment)
    make_customer(organization=manager.organization, segment=segment)

    response = authenticated_client(manager).post(f"{URL}/{segment.id}/deactivate")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SEGMENT_IN_USE"
    assert response.json()["error"]["details"] == {"active_customers": 2}
    segment.refresh_from_db()
    assert segment.is_active is True


def test_segment_with_only_inactive_customers_can_be_deactivated(manager: User) -> None:
    segment = make_segment(organization=manager.organization)
    make_customer(organization=manager.organization, segment=segment, is_active=False)

    response = authenticated_client(manager).post(f"{URL}/{segment.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert CustomerSegment.objects.get(id=segment.id).is_active is False


@pytest.mark.parametrize(
    ("role", "read", "manage"),
    [
        (Role.ADMIN, 200, 201),
        (Role.MANAGER, 200, 201),
        (Role.SALES, 200, 403),  # cadastra clientes, mas não define segmentos
        (Role.FINANCE, 200, 403),
        (Role.VIEWER, 200, 403),
        (Role.WAREHOUSE, 403, 403),
    ],
)
def test_permission_matrix(role: Role, read: int, manage: int) -> None:
    client = authenticated_client(make_user(role=role))

    assert client.get(URL).status_code == read
    assert client.post(URL, {"code": "NOVO", "name": "Novo"}).status_code == manage
