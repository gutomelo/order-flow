"""Autorização por permissões `resource:action` (docs/architecture/security.md).

`shared/` não conhece a política papel → permissões: ela pertence a `apps.identity`. Aqui fica
apenas a porta usada pelas views — qualquer usuário que implemente `PermissionSubject`.
"""

from typing import Any, Protocol, runtime_checkable

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


@runtime_checkable
class PermissionSubject(Protocol):
    def has_api_permission(self, permission: str) -> bool: ...


def HasPermission(*permissions: str) -> type[BasePermission]:
    """Permissão DRF que exige todas as `permissions` informadas.

    Uso: `permission_classes = [IsAuthenticated, HasPermission("users:manage")]`.
    """

    class _HasPermission(BasePermission):
        required = permissions

        def has_permission(self, request: Request, view: APIView) -> bool:
            user: Any = request.user
            if not (user and user.is_authenticated and isinstance(user, PermissionSubject)):
                return False
            return all(user.has_api_permission(permission) for permission in self.required)

    _HasPermission.__name__ = f"HasPermission[{','.join(permissions)}]"
    return _HasPermission


def HasReadWritePermission(*, read: str, write: str) -> type[BasePermission]:
    """`read` para métodos seguros (GET/HEAD/OPTIONS); `write` para os demais.

    Uso: `HasReadWritePermission(read="catalog:read", write="catalog:manage")`.
    """

    class _HasReadWritePermission(BasePermission):
        def has_permission(self, request: Request, view: APIView) -> bool:
            required = read if request.method in SAFE_METHODS else write
            return HasPermission(required)().has_permission(request, view)

    _HasReadWritePermission.__name__ = f"HasReadWritePermission[{read}|{write}]"
    return _HasReadWritePermission
