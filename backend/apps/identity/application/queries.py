"""Leituras públicas de usuários para outros módulos (notificações)."""

from dataclasses import dataclass
from uuid import UUID

from apps.identity.domain.permissions import Permission, Role, permissions_for
from apps.identity.models import User


@dataclass(frozen=True)
class UserContact:
    id: UUID
    email: str
    first_name: str


def active_users_with_permission(
    organization_id: UUID, permission: Permission
) -> list[UserContact]:
    """Quem deve ser avisado de algo: decidido pela permissão (RBAC), nunca por papel fixo."""
    roles = [role.value for role in Role if permission in permissions_for(role)]
    users = User.objects.filter(
        organization_id=organization_id, is_active=True, role__in=roles
    ).order_by("email")
    return [UserContact(user.id, user.email, user.first_name) for user in users]


def get_user_contact(user_id: UUID) -> UserContact | None:
    user = User.objects.filter(id=user_id).first()
    return None if user is None else UserContact(user.id, user.email, user.first_name)
