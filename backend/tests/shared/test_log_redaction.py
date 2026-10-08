import pytest

from shared.logging.processors import REDACTED, redact_sensitive_data

pytestmark = pytest.mark.unit


def test_redacts_sensitive_top_level_keys() -> None:
    event = {
        "event": "auth.login.failed",
        "username": "maria",
        "password": "s3cret",
        "refresh_token": "eyJ...",
        "Authorization": "Bearer eyJ...",
    }

    result = redact_sensitive_data(None, "info", event)

    assert result["username"] == "maria"
    assert result["password"] == REDACTED
    assert result["refresh_token"] == REDACTED
    assert result["Authorization"] == REDACTED


def test_redacts_sensitive_keys_in_nested_structures() -> None:
    event = {
        "event": "payments.gateway.request",
        "payload": {"amount": "10.00", "card_number": "4111111111111111"},
        "headers": [{"cookie": "sessionid=abc"}],
    }

    result = redact_sensitive_data(None, "info", event)

    assert result["payload"] == {"amount": "10.00", "card_number": REDACTED}
    assert result["headers"] == [{"cookie": REDACTED}]


def test_keeps_event_name_even_if_it_contains_sensitive_word() -> None:
    result = redact_sensitive_data(None, "info", {"event": "identity.token.refreshed"})

    assert result["event"] == "identity.token.refreshed"
