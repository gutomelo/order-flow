import pytest
from rest_framework.test import APIClient

pytestmark = [pytest.mark.integration, pytest.mark.urls("tests.urls")]


def test_domain_error_is_rendered_with_its_code_status_and_details(api_client: APIClient) -> None:
    response = api_client.get("/test/domain-error")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "INSUFFICIENT_STOCK",
            "message": "Estoque insuficiente.",
            "details": {"product_id": "p-1", "available": 0},
        }
    }


def test_validation_error_lists_invalid_fields(api_client: APIClient) -> None:
    response = api_client.post("/test/validation-error", {"quantity": 0}, format="json")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Os dados enviados são inválidos."
    assert list(error["details"]["fields"]) == ["quantity"]


def test_malformed_json_returns_malformed_request(api_client: APIClient) -> None:
    response = api_client.generic(
        "POST", "/test/validation-error", "{not json", content_type="application/json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MALFORMED_REQUEST"


def test_protected_view_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get("/test/protected")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_unexpected_error_hides_internal_details_and_returns_request_id(
    api_client: APIClient,
) -> None:
    response = api_client.get("/test/unexpected-error", HTTP_X_REQUEST_ID="req-12345678")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["details"] == {"request_id": "req-12345678"}
    assert "hunter2" not in response.content.decode()


def test_unknown_route_returns_json_not_found(api_client: APIClient) -> None:
    response = api_client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_method_not_allowed_uses_envelope(api_client: APIClient) -> None:
    response = api_client.delete("/test/domain-error")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_invalid_host_header_returns_json_bad_request(api_client: APIClient) -> None:
    response = api_client.get("/health/live", HTTP_HOST="evil.example.com")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
