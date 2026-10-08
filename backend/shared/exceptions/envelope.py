from collections.abc import Mapping
from typing import Any


def error_envelope(
    code: str, message: str, details: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Formato único de erro da API: {"error": {"code", "message", "details"}}."""
    return {"error": {"code": code, "message": message, "details": dict(details or {})}}
