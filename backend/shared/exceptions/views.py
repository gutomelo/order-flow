"""Handlers de erro do Django com o mesmo envelope de erro da API.

Cobrem requisições que não chegam a uma view DRF (rota inexistente, host inválido, falha em
middleware), garantindo que nenhuma resposta de erro saia como página HTML.
"""

from django.http import HttpRequest, JsonResponse

from shared.exceptions.envelope import error_envelope
from shared.exceptions.handler import INTERNAL_ERROR_MESSAGE
from shared.logging.context import get_request_id


def bad_request(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return JsonResponse(error_envelope("BAD_REQUEST", "Requisição inválida."), status=400)


def permission_denied(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return JsonResponse(
        error_envelope("PERMISSION_DENIED", "Você não tem permissão para executar esta ação."),
        status=403,
    )


def not_found(request: HttpRequest, exception: Exception | None = None) -> JsonResponse:
    return JsonResponse(error_envelope("NOT_FOUND", "Recurso não encontrado."), status=404)


def server_error(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        error_envelope("INTERNAL_ERROR", INTERNAL_ERROR_MESSAGE, {"request_id": get_request_id()}),
        status=500,
    )
