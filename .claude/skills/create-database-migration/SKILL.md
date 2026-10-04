---
name: create-database-migration
description: Cria e revisa migrations Django/PostgreSQL no OrderFlow com constraints, índices e segurança de deploy (sem locks longos, schema separado de data migration). Use ao alterar models ou adicionar constraints/índices.
argument-hint: <module> <descrição-da-mudança>
---

# Criar migration

Entrada: `$ARGUMENTS`

## 1. Modelar

- Leia `.claude/rules/database.md` e o doc de domínio do módulo.
- Invariantes críticas viram constraint (`CheckConstraint`, `UniqueConstraint` com nome explícito).
- FKs com `on_delete` deliberado (`PROTECT` para histórico/financeiro).
- Índices para as queries reais (filtros/ordenação da API, jobs periódicos). Índice parcial quando
  o filtro é seletivo.

## 2. Gerar

```bash
cd backend && uv run python manage.py makemigrations <module> --name <descricao_em_ingles>
```

Uma intenção por migration. Data migration (`RunPython`) separada da de schema, com função reversa
quando possível.

## 3. Revisar o SQL

```bash
cd backend && uv run python manage.py sqlmigrate <module> <numero>
```

Verifique: locks em tabelas grandes (`ALTER TABLE` com default volátil, `NOT NULL` direto, criação
de índice sem `CONCURRENTLY` em tabela grande), constraints validadas, nomes corretos.
Para mudanças arriscadas em tabelas grandes use expand/contract: coluna nullable → backfill →
constraint/NOT NULL.

## 4. Testar

- `migrate` do zero e (quando reversível) `migrate <module> <anterior>`.
- Teste que a constraint rejeita dado inválido (`IntegrityError`).
- `makemigrations --check --dry-run` sem pendências (faz parte do `backend:build`).

Para dúvidas de locking/performance, consulte o agent `database-engineer`.
