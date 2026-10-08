"""Convite e redefinição de senha até o e-mail (Phase 10, identity.md e notifications.md)."""

import re
from typing import Any

import pytest
from django.conf import settings
from django.core import mail
from rest_framework.test import APIClient

from apps.identity.domain.permissions import Role
from apps.identity.models import User
from apps.identity.tests.factories import DEFAULT_PASSWORD, authenticated_client, make_user
from apps.notifications.application.sending import send_notification
from apps.notifications.models import Notification
from shared.events.models import OutboxEvent
from shared.testing.events import drain_events

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

USERS = "/api/v1/users"
RESET = "/api/v1/auth/password-reset"
CONFIRM = "/api/v1/auth/password-reset/confirm"
NEW_PASSWORD = "Outra-Senha-Forte-2026!"
XHR: dict[str, Any] = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def _send_all() -> None:
    drain_events()
    for notification in Notification.objects.filter(status="PENDING"):
        send_notification(notification.id)


def _link(body: object) -> dict[str, str]:
    match = re.search(r"/reset-password#uid=([\w-]+)&token=([\w-]+)", str(body))
    assert match, body
    return {"uid": match.group(1), "token": match.group(2)}


def _login(email: str, password: str) -> Any:
    return APIClient().post("/api/v1/auth/login", {"email": email, "password": password})


@pytest.fixture
def admin() -> User:
    return make_user(role=Role.ADMIN)


def _invite(admin: User, email: str = "novo@acme.com") -> Any:
    # `password: null` explícito, como o frontend envia (omitir o campo também convida).
    return authenticated_client(admin).post(
        USERS,
        {"email": email, "first_name": "Bia", "role": "SALES", "password": None},
        format="json",
    )


# Convite ---------------------------------------------------------------------------------------


def test_a_user_created_without_password_is_invited_by_email_and_sets_it(admin: User) -> None:
    created = _invite(admin)
    assert created.status_code == 201
    assert created.json()["invitation_pending"] is True
    assert _login("novo@acme.com", "").status_code in (400, 401)  # sem senha ainda

    _send_all()

    (email,) = mail.outbox
    assert email.to == ["novo@acme.com"]
    assert email.subject.startswith("Convite para o OrderFlow")
    assert f"{settings.FRONTEND_URL}/reset-password#uid=" in email.body
    confirmed = APIClient().post(CONFIRM, {**_link(email.body), "password": NEW_PASSWORD})
    assert confirmed.status_code == 204
    assert _login("novo@acme.com", NEW_PASSWORD).status_code == 200
    user = authenticated_client(admin).get(f"{USERS}/{created.json()['id']}").json()
    assert user["invitation_pending"] is False


def test_the_link_works_only_once(admin: User) -> None:
    _invite(admin)
    _send_all()
    link = _link(mail.outbox[0].body)
    APIClient().post(CONFIRM, {**link, "password": NEW_PASSWORD})

    again = APIClient().post(CONFIRM, {**link, "password": "Mais-Uma-Senha-2026!"})

    assert again.status_code == 400
    assert again.json()["error"]["code"] == "INVALID_PASSWORD_RESET_TOKEN"


def test_a_weak_password_is_refused_with_the_reasons(admin: User) -> None:
    _invite(admin)
    _send_all()

    response = APIClient().post(CONFIRM, {**_link(mail.outbox[0].body), "password": "123"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WEAK_PASSWORD"
    error = response.json()["error"]
    assert error["details"]["field"] == "password"
    assert error["details"]["reasons"]
    assert error["message"].startswith("Esta senha é muito curta")  # política do Django, pt-BR


@pytest.mark.parametrize(
    "link",
    [
        {"uid": "bad", "token": "bad"},
        {"uid": "MQ", "token": "abc-123"},  # uid que não é UUID
    ],
)
def test_garbage_links_are_refused(link: dict[str, str]) -> None:
    response = APIClient().post(CONFIRM, {**link, "password": NEW_PASSWORD})

    assert response.json()["error"]["code"] == "INVALID_PASSWORD_RESET_TOKEN"


def test_an_invitation_can_be_sent_again_while_pending(admin: User) -> None:
    user_id = _invite(admin).json()["id"]
    client = authenticated_client(admin)

    resent = client.post(f"{USERS}/{user_id}/resend-invitation")
    _send_all()

    assert resent.status_code == 200
    assert len(mail.outbox) == 2
    APIClient().post(CONFIRM, {**_link(mail.outbox[1].body), "password": NEW_PASSWORD})
    refused = client.post(f"{USERS}/{user_id}/resend-invitation")
    assert refused.json()["error"]["code"] == "INVITATION_NOT_PENDING"


def test_inviting_requires_users_manage_and_stays_in_the_organization(admin: User) -> None:
    user_id = _invite(admin).json()["id"]
    manager = authenticated_client(make_user(role=Role.MANAGER, organization=admin.organization))
    stranger = authenticated_client(make_user(role=Role.ADMIN))

    assert manager.post(f"{USERS}/{user_id}/resend-invitation").status_code == 403
    assert stranger.post(f"{USERS}/{user_id}/resend-invitation").status_code == 404


# Esqueci a senha -------------------------------------------------------------------------------


def test_the_answer_is_the_same_whether_the_account_exists_or_not() -> None:
    make_user(email="ana@acme.com")
    make_user(email="inativa@acme.com", is_active=False)

    answers = [
        APIClient().post(RESET, {"email": email}).status_code
        for email in ("ana@acme.com", "ninguem@acme.com", "inativa@acme.com")
    ]
    _send_all()

    assert answers == [202, 202, 202]
    assert [m.to for m in mail.outbox] == [["ana@acme.com"]]
    assert Notification.objects.count() == 1  # conta inativa nem gera aviso


def test_resetting_the_password_ends_the_open_sessions() -> None:
    make_user(email="ana@acme.com")
    session = APIClient()
    session.post("/api/v1/auth/login", {"email": "ana@acme.com", "password": DEFAULT_PASSWORD})
    APIClient().post(RESET, {"email": "ANA@acme.com"})
    _send_all()

    APIClient().post(CONFIRM, {**_link(mail.outbox[0].body), "password": NEW_PASSWORD})

    assert session.post("/api/v1/auth/refresh", **XHR).status_code == 401
    assert _login("ana@acme.com", DEFAULT_PASSWORD).status_code == 401
    assert _login("ana@acme.com", NEW_PASSWORD).status_code == 200


def test_the_token_is_never_stored() -> None:
    make_user(email="ana@acme.com")
    APIClient().post(RESET, {"email": "ana@acme.com"})
    _send_all()
    token = _link(mail.outbox[0].body)["token"]

    stored = [str(e.payload) for e in OutboxEvent.objects.all()] + [
        f"{n.subject}{n.context}{n.last_error}" for n in Notification.objects.all()
    ]
    assert not any(token in text for text in stored)


def test_asking_for_reset_emails_is_throttled() -> None:
    client = APIClient()
    codes = [client.post(RESET, {"email": "x@acme.com"}).status_code for _ in range(6)]

    assert codes == [202] * 5 + [429]
