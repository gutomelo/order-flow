"""Catálogo de permissões e política papel → permissões.

Fonte única da autorização do sistema (docs/architecture/security.md#matriz-inicial). Alterar esta
política é uma decisão de produto: exige revisão e atualização da matriz documentada — o teste
`test_role_permission_matrix` compara as duas.
"""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    SALES = "SALES"
    WAREHOUSE = "WAREHOUSE"
    FINANCE = "FINANCE"
    VIEWER = "VIEWER"


class Permission(StrEnum):
    CUSTOMERS_READ = "customers:read"
    CUSTOMERS_CREATE = "customers:create"
    CUSTOMERS_UPDATE = "customers:update"
    CUSTOMERS_MANAGE_SEGMENTS = "customers:manage_segments"
    SUPPLIERS_READ = "suppliers:read"
    SUPPLIERS_MANAGE = "suppliers:manage"
    CATALOG_READ = "catalog:read"
    CATALOG_MANAGE = "catalog:manage"
    INVENTORY_READ = "inventory:read"
    INVENTORY_UPDATE = "inventory:update"
    INVENTORY_ADJUST = "inventory:adjust"
    ORDERS_READ = "orders:read"
    ORDERS_CREATE = "orders:create"
    ORDERS_CANCEL = "orders:cancel"
    ORDERS_CANCEL_PAID = "orders:cancel_paid"
    ORDERS_PROCESS = "orders:process"
    ORDERS_SHIP = "orders:ship"
    PAYMENTS_READ = "payments:read"
    PAYMENTS_CREATE = "payments:create"
    PAYMENTS_REFUND = "payments:refund"
    REPORTS_FINANCIAL = "reports:financial"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"


P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.MANAGER: frozenset(
        {
            P.CUSTOMERS_READ, P.CUSTOMERS_CREATE, P.CUSTOMERS_UPDATE, P.CUSTOMERS_MANAGE_SEGMENTS,
            P.SUPPLIERS_READ, P.SUPPLIERS_MANAGE,
            P.CATALOG_READ, P.CATALOG_MANAGE,
            P.INVENTORY_READ, P.INVENTORY_UPDATE, P.INVENTORY_ADJUST,
            P.ORDERS_READ, P.ORDERS_CREATE, P.ORDERS_CANCEL, P.ORDERS_CANCEL_PAID,
            P.ORDERS_PROCESS, P.ORDERS_SHIP,
            P.PAYMENTS_READ, P.PAYMENTS_CREATE,
            P.REPORTS_FINANCIAL,
            P.AUDIT_READ,
        }
    ),
    Role.SALES: frozenset(
        {
            P.CUSTOMERS_READ, P.CUSTOMERS_CREATE, P.CUSTOMERS_UPDATE,
            P.CATALOG_READ,
            P.INVENTORY_READ,
            P.ORDERS_READ, P.ORDERS_CREATE, P.ORDERS_CANCEL,
            P.PAYMENTS_CREATE,
        }
    ),
    Role.WAREHOUSE: frozenset(
        {
            P.SUPPLIERS_READ,
            P.CATALOG_READ,
            P.INVENTORY_READ, P.INVENTORY_UPDATE, P.INVENTORY_ADJUST,
            P.ORDERS_READ, P.ORDERS_PROCESS, P.ORDERS_SHIP,
        }
    ),
    Role.FINANCE: frozenset(
        {
            P.CUSTOMERS_READ,
            P.SUPPLIERS_READ,
            P.CATALOG_READ,
            P.ORDERS_READ, P.ORDERS_CANCEL_PAID,
            P.PAYMENTS_READ, P.PAYMENTS_CREATE, P.PAYMENTS_REFUND,
            P.REPORTS_FINANCIAL,
        }
    ),
    Role.VIEWER: frozenset(
        {
            P.CUSTOMERS_READ,
            P.SUPPLIERS_READ,
            P.CATALOG_READ,
            P.INVENTORY_READ,
            P.ORDERS_READ,
        }
    ),
}  # fmt: skip


def permissions_for(role: Role | str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(Role(role), frozenset())


def role_has_permission(role: Role | str, permission: Permission | str) -> bool:
    return permission in permissions_for(role)
