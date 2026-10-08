"""A política em código precisa ser idêntica à matriz documentada em security.md."""

import re
from pathlib import Path

import pytest

from apps.identity.domain.permissions import Permission, Role, permissions_for
from apps.identity.models import User

pytestmark = pytest.mark.unit

SECURITY_DOC = Path(__file__).resolve().parents[5] / "docs" / "architecture" / "security.md"


def _documented_matrix() -> dict[Role, set[str]]:
    """Lê a tabela "Matriz inicial" de security.md: linhas `| perm | ✓ | ... |`."""
    text = SECURITY_DOC.read_text(encoding="utf-8")
    section = text.split("### Matriz inicial", 1)[1].split("\n\n", 2)[1]
    lines = [line for line in section.splitlines() if line.startswith("|")]
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    roles = [Role(name) for name in header[1:]]
    matrix: dict[Role, set[str]] = {role: set() for role in roles}
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        # Uma linha pode documentar várias permissões: "`customers:create` / `customers:update`".
        permissions = re.findall(r"`([a-z_]+:[a-z_]+)`", cells[0])
        for role, cell in zip(roles, cells[1:], strict=True):
            if cell == "✓":
                matrix[role].update(permissions)
    return matrix


@pytest.mark.parametrize("role", list(Role))
def test_role_permission_matrix_matches_documentation(role: Role) -> None:
    assert {p.value for p in permissions_for(role)} == _documented_matrix()[role]


def test_every_permission_is_documented() -> None:
    documented = set().union(*_documented_matrix().values())

    assert {p.value for p in Permission} == documented


def test_only_admin_manages_users() -> None:
    allowed = [role for role in Role if Permission.USERS_MANAGE in permissions_for(role)]

    assert allowed == [Role.ADMIN]


def test_inactive_user_has_no_permissions() -> None:
    user = User(
        role=Role.ADMIN, is_active=False, organization_id="00000000-0000-0000-0000-000000000001"
    )

    assert user.has_api_permission(Permission.ORDERS_READ) is False


def test_platform_superuser_without_organization_has_no_api_permissions() -> None:
    user = User(role=Role.ADMIN, is_active=True, is_superuser=True, organization_id=None)

    assert user.has_api_permission(Permission.ORDERS_READ) is False
