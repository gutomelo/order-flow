---
paths:
  - "backend/apps/*/models.py"
  - "backend/apps/*/models/**"
  - "backend/apps/*/migrations/**"
---

# Banco de dados (PostgreSQL)

- **Multi-tenant (ADR-013):** todo model de negócio herda `shared.tenancy.models.TenantScopedModel`
  (FK `organization`). Unicidades de negócio incluem a organização (`UNIQUE (organization_id, sku)`).
  O teste `tests/architecture/test_tenant_scoping.py` falha se faltar.
- Toda invariante importante também no banco: `ForeignKey` com `on_delete` pensado
  (`PROTECT` para dados financeiros/históricos), `UniqueConstraint`, `CheckConstraint`.
- Nomes de constraints explícitos: `<table>_<rule>_check`, `<table>_<cols>_uniq`.
- Índices para filtros/ordenações reais da API; índices parciais quando o filtro é seletivo
  (ex.: reservas `ACTIVE` por `expires_at`).
- Dinheiro: `DecimalField(max_digits=14, decimal_places=2)`; quantidade de estoque:
  `PositiveIntegerField` ou `IntegerField` + `CheckConstraint`.
- Timestamps: `created_at`/`updated_at` timezone-aware. Tabelas append-only
  (`StockMovement`, `AuditLog`, `OrderStatusHistory`) não têm `updated_at` nem soft delete.
- Soft delete apenas onde decidido por entidade (customers, products) — nunca em movimentos,
  auditoria ou transações financeiras.
- Migrations: uma intenção por migration, nome descritivo (`--name add_stock_reservation`),
  sempre revisar o SQL (`sqlmigrate`). Migrations em tabelas grandes devem ser seguras para
  deploy (adicionar coluna nullable → backfill → constraint). Data migrations separadas de schema.
- Locking: `select_for_update()` somente dentro de `transaction.atomic()`, adquirindo locks em
  ordem determinística (por `id`) para evitar deadlock (ADR-008).
