from typing import Any

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import Token

from apps.identity.authentication import user_can_authenticate


class OrganizationAwareJWTAuthentication(JWTAuthentication):
    """JWT + verificação de organização ativa a cada requisição.

    O SimpleJWT só verifica `user.is_active` em tokens de acesso; suspender uma organização
    precisa cortar o acesso imediatamente, sem esperar o access token expirar (ADR-013).
    """

    def get_user(self, validated_token: Token) -> Any:
        user = super().get_user(validated_token)
        if not user_can_authenticate(user):
            raise AuthenticationFailed("Usuário ou organização inativos.", code="user_inactive")
        return user
