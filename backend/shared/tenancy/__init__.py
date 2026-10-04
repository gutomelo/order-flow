"""Isolamento entre organizações (ADR-013).

O model do tenant é configurado em `settings.TENANT_MODEL` (mesmo padrão de `AUTH_USER_MODEL`),
para que `shared/` não dependa de `apps/`.
"""
