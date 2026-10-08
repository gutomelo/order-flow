import uuid

import pytest
from django.test import Client

pytestmark = pytest.mark.integration


def test_generates_request_id_when_client_does_not_send_one(client: Client) -> None:
    response = client.get("/health/live")

    request_id = response["X-Request-ID"]
    assert uuid.UUID(request_id)


def test_reuses_valid_request_id_sent_by_client(client: Client) -> None:
    response = client.get("/health/live", HTTP_X_REQUEST_ID="frontend-req-0001")

    assert response["X-Request-ID"] == "frontend-req-0001"


@pytest.mark.parametrize(
    "unsafe_value",
    ["short", "x" * 65, "abc\r\nSet-Cookie: x=1", "spaces are not allowed"],
)
def test_replaces_unsafe_request_id_with_generated_one(client: Client, unsafe_value: str) -> None:
    response = client.get("/health/live", HTTP_X_REQUEST_ID=unsafe_value)

    assert response["X-Request-ID"] != unsafe_value
    assert uuid.UUID(response["X-Request-ID"])
