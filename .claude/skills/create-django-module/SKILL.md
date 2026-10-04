---
name: create-django-module
description: Cria um novo módulo de negócio (Django app) no backend do OrderFlow no nível de estrutura adequado à sua complexidade, registrado, com fronteiras no import-linter e documento de domínio. Use ao iniciar um módulo como catalog, inventory, orders, payments.
argument-hint: <module-name> [simple|rich]
arguments: [module, level]
---

# Criar módulo Django: `$module`

## 1. Validar antes de criar

- O módulo está na lista oficial (`CLAUDE.md` → Arquitetura)? Se não, pare e consulte o agent
  `software-architect`: módulo novo é decisão arquitetural.
- Leia `docs/architecture/backend.md` e, se existir, `docs/domain/$module.md`.
- Nível (`$level`): `simple` (CRUD com regras simples) ou `rich` (domínio com estados, invariantes,
  concorrência). Se não informado, decida pela complexidade descrita no doc de domínio e justifique.

## 2. Gerar a estrutura

Siga `.claude/templates/django-module.md`. Regras:
- Somente as pastas/arquivos que terão conteúdo **agora**. Nada de diretórios vazios.
- `apps.py` com `name = "apps.$module"` e `label = "$module"`.
- Nome de tudo em inglês.

## 3. Registrar

- `INSTALLED_APPS` em `backend/config/settings/base.py`.
- Rotas em `backend/config/urls.py` sob `api/v1/` (somente quando houver endpoint).
- Contratos do import-linter em `backend/pyproject.toml`: o módulo não importa `infrastructure`/`api`
  de outros módulos; camadas `api → application → domain` quando `rich`.

## 4. Documentar

- Crie/atualize `docs/domain/$module.md` a partir de `.claude/templates/domain-doc.md` e adicione ao
  índice `docs/domain/README.md`.
- Novos termos no `docs/domain/glossary.md`.

## 5. Verificar

`moon run backend:check` (inclui `lint-imports`). Reporte a estrutura criada e por que esse nível.
