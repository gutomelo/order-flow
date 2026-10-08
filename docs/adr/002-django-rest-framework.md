# ADR-002: Django + Django REST Framework no backend

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-001, ADR-004, ADR-007, `docs/architecture/backend.md`

## Context

Precisamos de um backend com ORM maduro, migrations, transações e locking no PostgreSQL, admin
para operação, autenticação, e uma API REST com paginação, filtros, permissões e OpenAPI. O projeto
também precisa demonstrar DDD pragmático sem abandonar a produtividade do framework.

## Decision

Usar **Python 3.13 + Django 5.2 LTS + Django REST Framework**, com:
- **drf-spectacular** para OpenAPI 3 (`/api/schema/`, `/api/docs/`);
- **djangorestframework-simplejwt** para JWT (ADR-007);
- **django-filter** para filtros declarativos;
- **uv** para dependências e ambiente virtual (lockfile `uv.lock`);
- **Ruff** (lint + format) e **mypy** com `django-stubs`/`djangorestframework-stubs`.

Django 5.2 é LTS (suporte de segurança até abril de 2028). A migração para a próxima LTS será feita
quando ela for lançada e o ecossistema (DRF, stubs, Celery) estiver compatível.

"Django continua sendo Django": models, migrations, admin e ORM são usados de forma idiomática.
Camadas `application`/`domain` são adicionadas apenas nos módulos com regras ricas (ADR-001).

## Alternatives Considered

### FastAPI + SQLAlchemy

- Prós: performance async, tipagem com Pydantic, OpenAPI nativo.
- Contras: admin, migrations (Alembic), auth, permissões e paginação precisam ser montados à mão;
  mais decisões de infraestrutura para um sistema majoritariamente transacional/CRUD-rico.
- Por que não: o gargalo do OrderFlow é correção transacional, não throughput de I/O.

### Django Ninja

- Prós: tipagem Pydantic, API moderna sobre Django.
- Contras: ecossistema de permissões, filtros e paginação menor que o do DRF; menos padrão de mercado.
- Por que não: DRF é o padrão mais reconhecido e suficiente; valor de portfólio maior.

### Django 6.x (não-LTS) em vez de 5.2 LTS

- Prós: recursos mais novos.
- Contras: janela de suporte curta; compatibilidade do ecossistema pode atrasar.
- Por que não: estabilidade e suporte longo valem mais para a fundação.

### Poetry / pip-tools em vez de uv

- Por que não: uv resolve e instala muito mais rápido, gerencia a versão do Python, tem lockfile
  multiplataforma e um único binário — menos peças no Docker e na CI.

## Consequences

### Positivas

- Produtividade alta, ecossistema maduro, padrão de mercado.
- Transações e `select_for_update` de primeira classe (ADR-008).
- Contrato OpenAPI gerado do código, consumível pelo frontend.

### Negativas / custos aceitos

- DRF é síncrono; aceitável (operações pesadas vão para Celery).
- Serializers tendem a acumular lógica: mitigado pela regra "API fina" e pelo `domain-reviewer`.

### Quando revisitar

Se surgirem requisitos de alta concorrência de I/O (ex.: streaming, websockets em larga escala) que
o modelo síncrono não atenda.
