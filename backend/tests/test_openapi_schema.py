import pytest
from django.test import Client

pytestmark = pytest.mark.integration


def test_openapi_schema_is_generated(client: Client) -> None:
    response = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "OrderFlow API"


def test_schema_documents_jwt_and_the_idempotency_key(client: Client) -> None:
    schema = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json").json()

    assert schema["components"]["securitySchemes"]["jwtAuth"]["scheme"] == "bearer"
    place_order = schema["paths"]["/api/v1/orders"]["post"]
    headers = {p["name"]: p for p in place_order["parameters"] if p["in"] == "header"}
    assert headers["Idempotency-Key"]["required"] is True
