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


def idempotent(operation: str) -> Callable[[ViewMethod], ViewMethod]:
    """Protege uma ação de view com `Idempotency-Key` (ADR-012).

    O registro e o efeito ficam na mesma transação: falha com rollback apaga o registro e a
    mesma chave pode ser reenviada. Só respostas 2xx são gravadas.
    """

    def decorator(view_method: ViewMethod) -> ViewMethod:
        @wraps(view_method)
        def wrapper(self: Any, request: Request, *args: Any, **kwargs: Any) -> Response:
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
                record.status = IdempotencyStatus.COMPLETED
                record.response_status = response.status_code
                record.response_body = json.loads(JSONRenderer().render(response.data))
                record.save(update_fields=["status", "response_status", "response_body"])
            return response

        return wrapper

    return decorator
