from typing import Any

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.identity.domain.permissions import Role
from apps.identity.models import Organization, User
from apps.identity.tests.factories import DEFAULT_PASSWORD, authenticated_client, make_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

COOKIE = settings.AUTH_REFRESH_COOKIE["name"]
XHR: dict[str, Any] = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def _login(client: APIClient, email: str, password: str = DEFAULT_PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/login", {"email": email, "password": password})


def test_login_returns_access_token_user_and_httponly_refresh_cookie() -> None:
    user = make_user(email="ana@acme.com", role=Role.SALES)
    client = APIClient()

    response = _login(client, "ANA@acme.com")  # e-mail sem diferenciar maiúsculas

    assert response.status_code == 200
    body = response.json()
    assert body["access"]
    assert body["user"]["email"] == "ana@acme.com"
    assert body["user"]["organization"]["id"] == str(user.organization_id)
    assert "orders:create" in body["user"]["permissions"]
    assert "users:manage" not in body["user"]["permissions"]
    assert "refresh" not in body  # nunca exposto a JavaScript
    cookie = response.cookies[COOKIE]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Strict"
    assert cookie["path"] == "/api/v1/auth/"


def test_access_token_authenticates_requests() -> None:
    user = make_user()
    client = APIClient()
    access = _login(client, user.email).json()["access"]

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


@pytest.mark.parametrize(
    "scenario", ["wrong_password", "unknown_email", "inactive_user", "inactive_organization"]
)
def test_login_failures_are_indistinguishable(scenario: str) -> None:
    user = make_user(email="bruno@acme.com")
    email, password = "bruno@acme.com", DEFAULT_PASSWORD
    if scenario == "wrong_password":
        password = "senha-errada"
    elif scenario == "unknown_email":
        email = "ninguem@acme.com"
    elif scenario == "inactive_user":
        User.objects.filter(pk=user.pk).update(is_active=False)
    else:
        Organization.objects.filter(users=user).update(is_active=False)

    response = _login(APIClient(), email, password)

    assert response.status_code == 401
    assert response.json()["error"] == {
        "code": "INVALID_CREDENTIALS",
        "message": "E-mail ou senha inválidos.",
        "details": {},
    }


def test_platform_superuser_cannot_use_the_business_api() -> None:
    User.objects.create_superuser("root@platform.com", DEFAULT_PASSWORD)

    assert _login(APIClient(), "root@platform.com").status_code == 401


def test_refresh_rotates_the_cookie_and_rejects_reuse_of_the_old_one() -> None:
    user = make_user()
    client = APIClient()
    _login(client, user.email)
    original = client.cookies[COOKIE].value

    first = client.post("/api/v1/auth/refresh", **XHR)

    assert first.status_code == 200
    assert first.json()["access"]
    assert client.cookies[COOKIE].value != original

    # Reuso de um refresh já rotacionado (indício de vazamento) é rejeitado.
    attacker = APIClient()
    attacker.cookies[COOKIE] = original
    reused = attacker.post("/api/v1/auth/refresh", **XHR)
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


def test_refresh_requires_the_anti_csrf_header() -> None:
    user = make_user()
    client = APIClient()
    _login(client, user.email)

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 403


def test_refresh_without_cookie_is_rejected_and_clears_cookie() -> None:
    response = APIClient().post("/api/v1/auth/refresh", **XHR)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"
    assert response.cookies[COOKIE]["max-age"] == 0


def test_logout_invalidates_the_refresh_token() -> None:
    user = make_user()
    client = APIClient()
    _login(client, user.email)
    refresh = client.cookies[COOKIE].value

    response = client.post("/api/v1/auth/logout", **XHR)

    assert response.status_code == 204
    replay = APIClient()
    replay.cookies[COOKIE] = refresh
    assert replay.post("/api/v1/auth/refresh", **XHR).status_code == 401


def test_logout_without_session_is_idempotent() -> None:
    assert APIClient().post("/api/v1/auth/logout", **XHR).status_code == 204


def test_suspending_the_organization_cuts_access_immediately() -> None:
    user = make_user()
    client = authenticated_client(user)
    assert client.get("/api/v1/auth/me").status_code == 200

    Organization.objects.filter(users=user).update(is_active=False)

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_suspended_organization_cannot_refresh_the_session() -> None:
    user = make_user()
    client = APIClient()
    _login(client, user.email)
    Organization.objects.filter(users=user).update(is_active=False)

    assert client.post("/api/v1/auth/refresh", **XHR).status_code == 401


def test_changing_password_invalidates_existing_access_tokens() -> None:
    user = make_user()
    client = authenticated_client(user)

    user.set_password("Outra-Senha-Forte-2026!")
    user.save()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_requests_without_token_get_401() -> None:
    response = APIClient().get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
    assert response.headers["WWW-Authenticate"].startswith("Bearer")


def test_login_is_rate_limited() -> None:
    client = APIClient()
    statuses = [_login(client, "x@acme.com", "errada").status_code for _ in range(11)]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
