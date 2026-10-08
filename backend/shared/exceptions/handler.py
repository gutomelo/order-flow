"""Exception handler global do DRF.

Toda resposta de erro da API sai no envelope padrão. Erros inesperados nunca expõem detalhes
internos ao cliente: a resposta traz apenas o `request_id`, e o stack trace fica no log.
"""

from typing import Any

import structlog
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

from shared.exceptions.base import DomainError
from shared.exceptions.envelope import error_envelope
from shared.logging.context import get_request_id
from shared.observability.metrics import API_ERRORS

logger = structlog.get_logger(__name__)

# Códigos estáveis para as exceções do DRF (o `default_code` do DRF nem sempre é o que queremos
# expor como contrato).
_API_EXCEPTION_CODES: dict[type[exceptions.APIException], str] = {
    exceptions.ValidationError: "VALIDATION_ERROR",
    exceptions.ParseError: "MALFORMED_REQUEST",
    exceptions.AuthenticationFailed: "AUTHENTICATION_FAILED",
    exceptions.NotAuthenticated: "NOT_AUTHENTICATED",
    exceptions.PermissionDenied: "PERMISSION_DENIED",
    exceptions.NotFound: "NOT_FOUND",
    exceptions.MethodNotAllowed: "METHOD_NOT_ALLOWED",
    exceptions.NotAcceptable: "NOT_ACCEPTABLE",
    exceptions.UnsupportedMediaType: "UNSUPPORTED_MEDIA_TYPE",
    exceptions.Throttled: "RATE_LIMITED",
}

VALIDATION_MESSAGE = "Os dados enviados são inválidos."
INTERNAL_ERROR_MESSAGE = "Ocorreu um erro inesperado. Tente novamente mais tarde."


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    response = _handle(exc, context)
    error = response.data.get("error", {}) if isinstance(response.data, dict) else {}
    API_ERRORS.labels(code=error.get("code", "UNKNOWN"), status=str(response.status_code)).inc()
    return response


def _handle(exc: Exception, context: dict[str, Any]) -> Response:
    if isinstance(exc, DomainError):
        set_rollback()
        return Response(error_envelope(exc.code, exc.message, exc.details), status=exc.http_status)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        set_rollback()
        return _api_exception_response(exc)

    set_rollback()
    logger.exception("api.unhandled_exception", view=_view_name(context))
    return Response(
        error_envelope("INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE, {"request_id": get_request_id()}),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _api_exception_response(exc: exceptions.APIException) -> Response:
    code = _API_EXCEPTION_CODES.get(type(exc), str(exc.default_code).upper())

    if isinstance(exc, exceptions.ValidationError):
        fields = exc.detail if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
        body = error_envelope(code, VALIDATION_MESSAGE, {"fields": fields})
    else:
        body = error_envelope(code, str(exc.detail))

    headers: dict[str, str] = {}
    auth_header = getattr(exc, "auth_header", None)
    if auth_header:
        headers["WWW-Authenticate"] = auth_header
    wait = getattr(exc, "wait", None)
    if wait:
        headers["Retry-After"] = str(int(wait))

    return Response(body, status=exc.status_code, headers=headers)


def _view_name(context: dict[str, Any]) -> str | None:
    view = context.get("view")
    return type(view).__name__ if view is not None else None
