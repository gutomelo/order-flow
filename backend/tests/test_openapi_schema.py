import pytest
from django.test import Client

pytestmark = pytest.mark.integration


def test_openapi_schema_is_generated(client: Client) -> None:
    response = client.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "OrderFlow API"
