import pytest

from apps.identity.application.commands.users import ChangeUserRole, ChangeUserRoleCommand
from apps.identity.domain.exceptions import LastAdminRequired
from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import (
    authenticated_client,
    make_organization,
    make_team,
    make_user,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def admin() -> User:
    return make_user(role=Role.ADMIN)


def _new_user_payload(**overrides: object) -> dict[str, object]:
    return {
        "email": "nova@acme.com",
        "password": "Pedido-Seguro-2026!",
        "first_name": "Nova",
        "last_name": "Pessoa",
        "role": "SALES",
        **overrides,
    }


@pytest.mark.parametrize("role", [r for r in Role if r is not Role.ADMIN])
def test_only_admins_can_manage_users(role: Role) -> None:
    client = authenticated_client(make_user(role=role))

    assert client.get("/api/v1/users").status_code == 403
    assert client.post("/api/v1/users", _new_user_payload()).status_code == 403


def test_admin_creates_user_in_own_organization(admin: User) -> None:
    team = make_team(organization=admin.organization)

    response = authenticated_client(admin).post(
        "/api/v1/users", _new_user_payload(team_id=str(team.id))
    )

    assert response.status_code == 201
    created = User.objects.get(email="nova@acme.com")
    assert created.organization_id == admin.organization_id
    assert created.team == team
    assert created.check_password("Pedido-Seguro-2026!")
    assert "password" not in response.json()


def test_organization_cannot_be_chosen_by_the_client(admin: User) -> None:
    other = make_organization()

    authenticated_client(admin).post("/api/v1/users", _new_user_payload(organization=str(other.id)))

    assert User.objects.get(email="nova@acme.com").organization_id == admin.organization_id


def test_weak_password_is_rejected_with_field_error(admin: User) -> None:
    response = authenticated_client(admin).post("/api/v1/users", _new_user_payload(password="123"))

    assert response.status_code == 400
    assert "password" in response.json()["error"]["details"]["fields"]


def test_duplicated_email_is_rejected_case_insensitively(admin: User) -> None:
    make_user(email="nova@acme.com")

    response = authenticated_client(admin).post(
        "/api/v1/users", _new_user_payload(email="NOVA@acme.com")
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_IN_USE"


def test_team_from_another_organization_is_rejected(admin: User) -> None:
    foreign_team = make_team()

    response = authenticated_client(admin).post(
        "/api/v1/users", _new_user_payload(team_id=str(foreign_team.id))
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TEAM_NOT_FOUND"


def test_listing_only_shows_users_of_the_same_organization(admin: User) -> None:
    colleague = make_user(organization=admin.organization)
    make_user()  # outra organização

    response = authenticated_client(admin).get("/api/v1/users")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["results"]}
    assert ids == {str(admin.id), str(colleague.id)}


def test_users_of_other_organizations_are_not_found(admin: User) -> None:
    stranger = make_user(role=Role.SALES)
    client = authenticated_client(admin)

    assert client.get(f"/api/v1/users/{stranger.id}").status_code == 404
    assert client.patch(f"/api/v1/users/{stranger.id}", {"first_name": "X"}).status_code == 404
    response = client.post(f"/api/v1/users/{stranger.id}/change-role", {"role": "ADMIN"})
    assert response.status_code == 404
    stranger.refresh_from_db()
    assert stranger.role == Role.SALES


def test_listing_supports_search_and_filters(admin: User) -> None:
    make_user(organization=admin.organization, first_name="Carla", role=Role.FINANCE)
    make_user(organization=admin.organization, first_name="Diego", role=Role.SALES)
    client = authenticated_client(admin)

    by_search = client.get("/api/v1/users", {"search": "carla"}).json()
    by_role = client.get("/api/v1/users", {"role": "SALES"}).json()

    assert [u["first_name"] for u in by_search["results"]] == ["Carla"]
    assert [u["first_name"] for u in by_role["results"]] == ["Diego"]


def test_patch_updates_profile_and_can_clear_team(admin: User) -> None:
    team = make_team(organization=admin.organization)
    member = make_user(organization=admin.organization, team=team)

    response = authenticated_client(admin).patch(
        f"/api/v1/users/{member.id}", {"first_name": "Renomeado", "team_id": None}, format="json"
    )

    assert response.status_code == 200
    member.refresh_from_db()
    assert member.first_name == "Renomeado"
    assert member.team is None


def test_patch_cannot_change_role_or_status(admin: User) -> None:
    member = make_user(organization=admin.organization, role=Role.VIEWER)

    authenticated_client(admin).patch(
        f"/api/v1/users/{member.id}", {"role": "ADMIN", "is_active": False}, format="json"
    )

    member.refresh_from_db()
    assert member.role == Role.VIEWER
    assert member.is_active is True


def test_admin_changes_role_and_new_permissions_apply_immediately(admin: User) -> None:
    member = make_user(organization=admin.organization, role=Role.VIEWER)
    member_client = authenticated_client(member)
    assert member_client.get("/api/v1/users").status_code == 403

    response = authenticated_client(admin).post(
        f"/api/v1/users/{member.id}/change-role", {"role": "ADMIN"}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert member_client.get("/api/v1/users").status_code == 200  # mesmo token


def test_admin_cannot_change_own_role(admin: User) -> None:
    response = authenticated_client(admin).post(
        f"/api/v1/users/{admin.id}/change-role", {"role": "VIEWER"}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SELF_MANAGEMENT_NOT_ALLOWED"


def test_admin_can_demote_another_admin(admin: User) -> None:
    other_admin = make_user(organization=admin.organization, role=Role.ADMIN)

    response = authenticated_client(admin).post(
        f"/api/v1/users/{other_admin.id}/change-role", {"role": "SALES"}
    )

    assert response.status_code == 200


def test_use_case_rejects_removing_the_last_active_admin() -> None:
    # Pela API a regra só é atingível por corrida (só ADMIN gerencia usuários e ninguém gerencia
    # a si mesmo); aqui ela é exercitada diretamente no use case. ADMIN inativo não conta.
    admin = make_user(role=Role.ADMIN)
    make_user(organization=admin.organization, role=Role.ADMIN, is_active=False)
    actor = make_user(organization=admin.organization, role=Role.MANAGER)

    assert admin.organization_id is not None
    with pytest.raises(LastAdminRequired):
        ChangeUserRole().execute(
            ChangeUserRoleCommand(
                organization_id=admin.organization_id,
                actor_id=actor.id,
                user_id=admin.id,
                role=Role.SALES,
            )
        )
    admin.refresh_from_db()
    assert admin.role == Role.ADMIN


def test_deactivated_user_loses_access_on_next_request(admin: User) -> None:
    member = make_user(organization=admin.organization, role=Role.ADMIN)
    member_client = authenticated_client(member)

    response = authenticated_client(admin).post(f"/api/v1/users/{member.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert member_client.get("/api/v1/auth/me").status_code == 401


def test_admin_cannot_deactivate_themselves(admin: User) -> None:
    response = authenticated_client(admin).post(f"/api/v1/users/{admin.id}/deactivate")

    assert response.status_code == 409


def test_reactivating_a_user_restores_access(admin: User) -> None:
    member = make_user(organization=admin.organization, is_active=False)

    response = authenticated_client(admin).post(f"/api/v1/users/{member.id}/activate")

    assert response.status_code == 200
    member.refresh_from_db()
    assert member.is_active is True
