"""Regras de administração de usuários (docs/domain/identity.md, invariantes ID5 e ID6)."""

from uuid import UUID

from apps.identity.domain.exceptions import LastAdminRequired, SelfManagementNotAllowed
from apps.identity.domain.permissions import Role


def ensure_not_managing_self(actor_id: UUID, target_id: UUID) -> None:
    """ID6: ninguém altera o próprio papel nem se desativa (evita perda acidental de acesso)."""
    if actor_id == target_id:
        raise SelfManagementNotAllowed()


def ensure_admin_remains(
    *, target_is_active_admin: bool, target_will_be_active_admin: bool, other_active_admins: int
) -> None:
    """ID5: a organização mantém pelo menos um ADMIN ativo após a mudança."""
    loses_an_admin = target_is_active_admin and not target_will_be_active_admin
    if loses_an_admin and other_active_admins == 0:
        raise LastAdminRequired()


def is_active_admin(*, role: Role | str, is_active: bool) -> bool:
    return is_active and Role(role) is Role.ADMIN
