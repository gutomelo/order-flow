from dataclasses import dataclass

import structlog
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.identity.authentication import user_can_authenticate
from apps.identity.domain.exceptions import InvalidCredentials, InvalidRefreshToken
from apps.identity.models import User, normalize_email

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str


@dataclass(frozen=True)
class LoginResult:
    user: User
    tokens: TokenPair


class Login:
    """Autentica por e-mail e senha e emite access + refresh (ADR-007)."""

    def execute(self, request: HttpRequest | None, *, email: str, password: str) -> LoginResult:
        user = authenticate(request, username=normalize_email(email), password=password)
        if not isinstance(user, User) or not user_can_authenticate(user):
            # Um único erro para todos os motivos: não revela quais contas existem.
            logger.info("identity.login.failed")
            raise InvalidCredentials()

        refresh = RefreshToken.for_user(user)
        update_last_login(User, user)
        logger.info("identity.login.succeeded", user_id=str(user.id))
        return LoginResult(user=user, tokens=TokenPair(str(refresh.access_token), str(refresh)))


class RefreshSession:
    """Troca um refresh válido por um novo par (rotação + blacklist do refresh anterior)."""

    def execute(self, raw_refresh: str | None) -> TokenPair:
        if not raw_refresh:
            raise InvalidRefreshToken()
        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (APIException, TokenError, ObjectDoesNotExist) as exc:
            # Expirado, adulterado, já rotacionado (blacklist), usuário/organização inativos.
            logger.info("identity.refresh.rejected", reason=type(exc).__name__)
            raise InvalidRefreshToken() from exc
        data = serializer.validated_data
        return TokenPair(access=data["access"], refresh=data["refresh"])


class Logout:
    """Invalida o refresh token atual. Idempotente: token ausente/inválido não é erro."""

    def execute(self, raw_refresh: str | None) -> None:
        if not raw_refresh:
            return
        try:
            RefreshToken(raw_refresh).blacklist()  # type: ignore[arg-type]
        except TokenError:
            return
        logger.info("identity.logout")
