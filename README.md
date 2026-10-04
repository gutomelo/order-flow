# OrderFlow

Plataforma B2B de gestão de pedidos e estoque — Django/DRF + Vue 3/TypeScript em um monorepo
poliglota coordenado pelo Moonrepo.

> **Status:** Phase 0 — Context Engineering. A fundação de arquitetura, decisões e convenções está
> documentada; a implementação começa na Phase 1.

## Por onde começar

| Documento | Conteúdo |
| --- | --- |
| [CLAUDE.md](CLAUDE.md) | Contexto central do projeto (regras, stack, comandos, Definition of Done) |
| [docs/architecture/overview.md](docs/architecture/overview.md) | Visão geral da arquitetura e roadmap |
| [docs/adr/](docs/adr/README.md) | Architecture Decision Records |
| [docs/domain/](docs/domain/README.md) | Modelo de domínio, glossário, regras de pedidos e estoque |
| [docs/development/](docs/development/local-development.md) | Padrões de código, testes, git e ambiente local |
| [docs/diagrams/](docs/diagrams/c4-model.md) | Diagramas C4 e fluxos |

## Stack

Python 3.13 · Django 5.2 LTS · DRF · Celery · RabbitMQ · PostgreSQL · Redis · Vue 3 · TypeScript ·
Vite · Pinia · TanStack Query · Moonrepo · Docker Compose · GitHub Actions
