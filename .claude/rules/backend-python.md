---
paths:
  - "backend/**/*.py"
  - "backend/pyproject.toml"
---

# Backend Python / Django

- Python 3.13, Django 5.2 LTS, DRF. Dependências gerenciadas por `uv` (`uv add`, `uv.lock` versionado).
- Ruff faz lint **e** formatação (sem Black/isort). mypy com `django-stubs` e
  `djangorestframework-stubs`; código novo deve passar no mypy sem `# type: ignore` sem justificativa.
- Type hints em todas as funções públicas. `from __future__ import annotations` não é necessário.
- Dinheiro: `Decimal` + `shared.domain.money.Money`; nunca `float`. Quantização centralizada.
- Datas: `django.utils.timezone.now()`; nunca `datetime.now()` ingênuo. `USE_TZ = True`.
- IDs públicos: UUID (`id = UUIDField(primary_key=True, default=uuid4)`) em entidades expostas
  na API. Nunca expor IDs sequenciais.
- Transações: `transaction.atomic()` na camada **application** (use case), não em views nem no domínio.
- Efeitos pós-commit: `transaction.on_commit(...)`. Nunca enfileirar Celery dentro de transação
  aberta sem `on_commit`.
- Signals do Django: evitar para regra de negócio (fluxo implícito). Use Domain Events explícitos.
- Exceções de domínio herdam de `shared.exceptions.DomainError` e carregam `code` estável;
  o exception handler global as converte para o envelope de erro.
- Queries: `select_related`/`prefetch_related` em listagens; nada de query dentro de loop.
- Logging: `structlog` via `shared.logging`; eventos nomeados `module.entity.action`
  (ex.: `orders.order.created`), contexto como chaves, nunca f-strings com dados sensíveis.
- Configuração via variáveis de ambiente (`config/settings/`), com valores seguros por padrão.
