"""Endpoints de sessão (ADR-007): access token no corpo, refresh token em cookie HttpOnly."""

from typing import Any, cast

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.identity.api.serializers import (
    AccessTokenSerializer,
    CurrentUserSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from apps.identity.application import passwords
from apps.identity.application.commands.authenticate import Login, Logout, RefreshSession
from apps.identity.domain.exceptions import InvalidRefreshToken
from apps.identity.models import User
from shared.exceptions.envelope import error_envelope


class RequiresXRequestedWith(BasePermission):
    """Defesa extra contra CSRF nos endpoints que usam o cookie de refresh.

    Formulários e links de outros sites não conseguem enviar headers customizados; um `fetch`
    cross-origin com esse header dispara preflight e é barrado pelo CORS.
    """

    message = "Requisição inválida."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _cookie_config() -> dict[str, Any]:
    config: dict[str, Any] = settings.AUTH_REFRESH_COOKIE
    return config


def _set_refresh_cookie(response: Response, refresh: str) -> None:
    config = _cookie_config()
    response.set_cookie(
        config["name"],
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=config["path"],
        secure=config["secure"],
        httponly=True,
        samesite=config["samesite"],
    )


def _delete_refresh_cookie(response: Response) -> None:
    config = _cookie_config()
    response.delete_cookie(config["name"], path=config["path"], samesite=config["samesite"])


def _refresh_from_cookie(request: Request) -> str | None:
    value: str | None = request.COOKIES.get(_cookie_config()["name"])
    return value


class AuthEndpoint(APIView):
    # Endpoints de sessão não dependem de um access token válido.
    authentication_classes = ()
    permission_classes: tuple[type[BasePermission], ...] = (AllowAny,)


class LoginView(AuthEndpoint):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth"

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            401: OpenApiResponse(description="INVALID_CREDENTIALS"),
        },
        summary="Inicia sessão",
        description="Retorna o access token e define o refresh token em cookie HttpOnly.",
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = Login().execute(request._request, **serializer.validated_data)
        response = Response(
            {"access": result.tokens.access, "user": CurrentUserSerializer(result.user).data}
        )
        _set_refresh_cookie(response, result.tokens.refresh)
        return response


class RefreshView(AuthEndpoint):
    permission_classes = (AllowAny, RequiresXRequestedWith)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth"

    @extend_schema(
        request=None,
        responses={
            200: AccessTokenSerializer,
            401: OpenApiResponse(description="INVALID_REFRESH_TOKEN"),
        },
        summary="Renova a sessão",
        description="Usa o cookie de refresh, rotaciona-o e retorna um novo access token. "
        "Exige o header `X-Requested-With: XMLHttpRequest`.",
    )
    def post(self, request: Request) -> Response:
        try:
            tokens = RefreshSession().execute(_refresh_from_cookie(request))
        except InvalidRefreshToken as exc:
            # Sessão inválida: além do erro, remove o cookie para o navegador não reenviá-lo.
            response = Response(
                error_envelope(exc.code, exc.message), status=status.HTTP_401_UNAUTHORIZED
            )
            _delete_refresh_cookie(response)
            return response
        response = Response({"access": tokens.access})
        _set_refresh_cookie(response, tokens.refresh)
        return response


class LogoutView(AuthEndpoint):
    permission_classes = (AllowAny, RequiresXRequestedWith)

    @extend_schema(request=None, responses={204: None}, summary="Encerra a sessão")
    def post(self, request: Request) -> Response:
        Logout().execute(_refresh_from_cookie(request))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _delete_refresh_cookie(response)
        return response


class PasswordResetRequestView(AuthEndpoint):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={202: None},
        summary="Pede o e-mail de redefinição de senha",
        description="Responde 202 exista ou não a conta: não revela quais e-mails existem.",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        passwords.request_password_reset(serializer.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(AuthEndpoint):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth"

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            204: None,
            400: OpenApiResponse(description="INVALID_PASSWORD_RESET_TOKEN"),
            422: OpenApiResponse(description="WEAK_PASSWORD"),
        },
        summary="Define a senha (convite ou redefinição)",
        description="Encerra as sessões abertas do usuário; ele entra de novo com a senha nova.",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        passwords.reset_password(data["uid"], data["token"], data["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(responses=CurrentUserSerializer, summary="Usuário autenticado")
    def get(self, request: Request) -> Response:
        return Response(CurrentUserSerializer(cast(User, request.user)).data)
