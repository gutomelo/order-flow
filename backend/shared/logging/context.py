import structlog


def get_request_id() -> str | None:
    """`request_id` da requisição atual (vinculado pelo RequestIdMiddleware), se houver."""
    value = structlog.contextvars.get_contextvars().get("request_id")
    return str(value) if value is not None else None
