import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any, Concatenate
from uuid import UUID

import structlog
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response

from shared.exceptions import DomainError
from shared.exceptions.envelope import error_envelope
from shared.idempotency.exceptions import (
    IdempotencyKeyRequired,
    IdempotencyKeyReused,
    IdempotencyRequestInProgress,
)
from shared.idempotency.models import IdempotencyRecord, IdempotencyStatus

logger = structlog.get_logger(__name__)

HEADER = "Idempotency-Key"
REPLAY_HEADER = "Idempotent-Replayed"
TTL = timedelta(hours=24)

ViewMethod = Callable[Concatenate[Any, Request, ...], Response]


def _key_of(request: Request) -> UUID:
    raw = request.headers.get(HEADER, "")
    try:
        return UUID(raw)
    except ValueError:
        raise IdempotencyKeyRequired() from None


def _fingerprint(request: Request) -> str:
    """Hash do método, caminho e corpo normalizado: a mesma intenção gera o mesmo valor."""
    body = json.dumps(request.data, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{request.method}\n{request.path}\n{body}".encode()).hexdigest()


def _claim(
    request: Request, operation: str, key: UUID, fingerprint: str
) -> tuple[IdempotencyRecord, Response | None]:
    user: Any = request.user
    now = timezone.now()
    lookup = {"user_id": user.id, "operation": operation, "key": key}
    try:
        with transaction.atomic():
            # Duas requisições iguais ao mesmo tempo: a segunda espera aqui (índice único) até a
            # primeira concluir — e então cai no `except` e devolve a resposta gravada.
            record = IdempotencyRecord.objects.create(
                **lookup,
                organization_id=user.organization_id,
                fingerprint=fingerprint,
                status=IdempotencyStatus.IN_PROGRESS,
                expires_at=now + TTL,
            )
        return record, None
    except IntegrityError:
        existing = IdempotencyRecord.objects.select_for_update().get(**lookup)

    if existing.expires_at <= now:
        existing.delete()
        return _claim(request, operation, key, fingerprint)
    if existing.fingerprint != fingerprint:
        raise IdempotencyKeyReused()
    if existing.status == IdempotencyStatus.IN_PROGRESS:
        raise IdempotencyRequestInProgress()
    logger.info("idempotency.replayed", operation=operation)
    replay = Response(existing.response_body, status=existing.response_status)
    replay[REPLAY_HEADER] = "true"
    return existing, replay


def _complete(record: IdempotencyRecord, response: Response) -> None:
    record.status = IdempotencyStatus.COMPLETED
    record.response_status = response.status_code
    record.response_body = json.loads(JSONRenderer().render(response.data))
    record.save(update_fields=["status", "response_status", "response_body"])


def _run_in_steps(
    view_method: ViewMethod, operation: str, view: Any, request: Request, *args: Any, **kwargs: Any
) -> Response:
    """Operação de várias transações (pagamento: chamada ao gateway entre elas).

    O registro IN_PROGRESS é commitado antes: outra requisição com a mesma chave recebe
    `IDEMPOTENCY_REQUEST_IN_PROGRESS` em vez de cobrar de novo. Erro de domínio (ex.: cartão
    recusado) é desfecho da intenção e também é gravado; erro inesperado apaga o registro.
    """
    key = _key_of(request)
    fingerprint = _fingerprint(request)
    with transaction.atomic():
        record, replay = _claim(request, operation, key, fingerprint)
    if replay is not None:
        return replay
    try:
        response = view_method(view, request, *args, **kwargs)
    except DomainError as exc:
        response = Response(error_envelope(exc.code, exc.message, exc.details), exc.http_status)
    except Exception:
        IdempotencyRecord.objects.filter(id=record.id).delete()
        raise
    if response.status_code >= 500 or response.status_code < 200:
        IdempotencyRecord.objects.filter(id=record.id).delete()
        return response
    _complete(record, response)
    return response


def idempotent(operation: str, *, atomic: bool = True) -> Callable[[ViewMethod], ViewMethod]:
    """Protege uma ação de view com `Idempotency-Key` (ADR-012).

    `atomic=True` (padrão): registro e efeito na mesma transação; falha com rollback apaga o
    registro e a mesma chave pode ser reenviada. Só respostas 2xx são gravadas.
    `atomic=False`: operações de várias transações (ver `_run_in_steps`).
    """

    def decorator(view_method: ViewMethod) -> ViewMethod:
        @wraps(view_method)
        def wrapper(self: Any, request: Request, *args: Any, **kwargs: Any) -> Response:
            if not atomic:
                return _run_in_steps(view_method, operation, self, request, *args, **kwargs)
            key = _key_of(request)
            fingerprint = _fingerprint(request)
            with transaction.atomic():
                record, replay = _claim(request, operation, key, fingerprint)
                if replay is not None:
                    return replay
                response = view_method(self, request, *args, **kwargs)
                if not 200 <= response.status_code < 300:
                    transaction.set_rollback(True)
                    return response
                _complete(record, response)
            return response

        return wrapper

    return decorator
