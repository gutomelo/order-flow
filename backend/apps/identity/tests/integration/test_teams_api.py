import pytest

from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import authenticated_client, make_team, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def admin() -> User:
    return make_user(role=Role.ADMIN)


def test_admin_creates_team(admin: User) -> None:
    response = authenticated_client(admin).post("/api/v1/teams", {"name": "  Comercial Sul  "})

    assert response.status_code == 201
    assert response.json()["name"] == "Comercial Sul"
    assert response.json()["member_count"] == 0


def test_team_names_are_unique_per_organization_ignoring_case(admin: User) -> None:
    make_team(organization=admin.organization, name="Comercial")
    make_team(name="Expedição")  # mesmo nome em outra organização é permitido abaixo

    duplicated = authenticated_client(admin).post("/api/v1/teams", {"name": "COMERCIAL"})
    other_org_name = authenticated_client(admin).post("/api/v1/teams", {"name": "Expedição"})

    assert duplicated.status_code == 409
    assert duplicated.json()["error"]["code"] == "TEAM_NAME_ALREADY_IN_USE"
    assert other_org_name.status_code == 201


def test_list_is_scoped_and_counts_members(admin: User) -> None:
    team = make_team(organization=admin.organization)
    make_user(organization=admin.organization, team=team)
    make_team()  # outra organização

    response = authenticated_client(admin).get("/api/v1/teams")

    results = response.json()["results"]
    assert [(t["id"], t["member_count"]) for t in results] == [(str(team.id), 1)]


def test_rename_team(admin: User) -> None:
    team = make_team(organization=admin.organization, name="Antigo")

    response = authenticated_client(admin).patch(f"/api/v1/teams/{team.id}", {"name": "Novo"})

    assert response.status_code == 200
    assert response.json()["name"] == "Novo"


def test_team_of_other_organization_is_not_found(admin: User) -> None:
    foreign = make_team()

    response = authenticated_client(admin).patch(f"/api/v1/teams/{foreign.id}", {"name": "X"})

    assert response.status_code == 404


def test_non_admin_cannot_manage_teams() -> None:
    client = authenticated_client(make_user(role=Role.MANAGER))

    assert client.post("/api/v1/teams", {"name": "X"}).status_code == 403
