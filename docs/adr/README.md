# Architecture Decision Records

Cada ADR registra **uma** decisão arquitetural: o problema, a decisão, as alternativas e as
consequências aceitas. ADRs aceitos não são reescritos — uma nova decisão cria um novo ADR e marca o
anterior como `Superseded by ADR-NNN`.

Template: `.claude/templates/adr.md` · Criação: skill `/create-adr`.

| ADR | Título | Status |
| --- | --- | --- |
| [001](001-modular-monolith.md) | Modular Monolith como arquitetura inicial | Accepted |
| [002](002-django-rest-framework.md) | Django + Django REST Framework no backend | Accepted |
| [003](003-vue-typescript.md) | Vue 3 + TypeScript no frontend, TanStack Query para server state | Accepted |
| [004](004-postgresql.md) | PostgreSQL como banco principal e guardião de invariantes | Accepted |
| [005](005-rabbitmq-celery.md) | RabbitMQ como broker e Celery para processamento assíncrono | Accepted |
| [006](006-redis.md) | Redis para cache e throttling (uso restrito) | Accepted |
| [007](007-jwt-authentication.md) | Autenticação JWT com SimpleJWT, rotação e blacklist | Accepted |
| [008](008-stock-concurrency-control.md) | Controle de concorrência de estoque com lock pessimista | Accepted |
| [009](009-moonrepo.md) | Moonrepo como coordenador do monorepo poliglota | Accepted |
| [010](010-docker-compose-local-environment.md) | Docker Compose para o ambiente local | Accepted |
| [011](011-transactional-outbox.md) | Transactional Outbox para eventos críticos | Proposed |
| [012](012-idempotency-keys.md) | Idempotency-Key persistida no PostgreSQL | Accepted |

## Status possíveis

- **Proposed** — em avaliação; ainda não guia implementação.
- **Accepted** — vigente.
- **Deprecated** — não se aplica mais, sem substituto.
- **Superseded by ADR-NNN** — substituído.
