import pytest
from django.test import Client

from shared.infrastructure import health

pytestmark = pytest.mark.integration


def _broker_ok() -> None:
    return None


def _broker_down() -> None:
    raise ConnectionRefusedError("amqp://orderflow:secret@rabbitmq:5672 refused")


def test_liveness_does_not_depend_on_external_services(client: Client) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_is_ok_when_all_dependencies_respond(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(health.READINESS_CHECKS, "broker", _broker_ok)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "cache": "ok", "broker": "ok"},
    }


@pytest.mark.django_db
def test_readiness_reports_unavailable_dependency_without_leaking_details(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(health.READINESS_CHECKS, "broker", _broker_down)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["broker"] == "unavailable"
    assert "secret" not in response.content.decode()


def test_health_endpoints_only_accept_get(client: Client) -> None:
    assert client.post("/health/live").status_code == 405
