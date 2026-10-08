from typing import Any


def user_can_authenticate(user: Any) -> bool:
    """Regra única de autenticação (login, refresh e cada requisição) — invariante ID7.

    Apenas usuários ativos de organizações ativas usam a API. Superusuários da plataforma não têm
    organização e, portanto, só acessam o Django admin.
    """
    if user is None or not user.is_active or user.organization_id is None:
        return False
    return bool(user.organization.is_active)
