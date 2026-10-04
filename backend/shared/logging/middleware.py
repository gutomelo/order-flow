"""Request ID e log de acesso estruturado."""

import re
import time
import uuid
from collections.abc import Callable

import structlog
from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER = "X-Request-ID"

# Aceita o ID enviado pelo cliente apenas se for "seguro" (evita injeção em logs/headers).
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")

logger = structlog.get_logger("shared.http")


class RequestIdMiddleware:
    """Gera (ou aceita) um `request_id` por requisição e o propaga para logs e resposta.

    O `correlation_id` nasce igual ao `request_id`; eventos e tasks futuras o propagam para
    acompanhar um fluxo inteiro (docs/architecture/observability.md).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = self._resolve_request_id(request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, correlation_id=request_id)

        started = time.perf_counter()
        try:
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            logger.info(
                "http.request.completed",
                method=request.method,
                path=request.path,  # sem query string: pode conter dados sensíveis
                status=response.status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()

    @staticmethod
    def _resolve_request_id(request: HttpRequest) -> str:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        if _VALID_REQUEST_ID.fullmatch(incoming):
            return incoming
        return str(uuid.uuid4())
