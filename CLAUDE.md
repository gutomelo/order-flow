# OrderFlow — Contexto do Projeto

Plataforma B2B de gestão de pedidos e estoque. Projeto funcional **e** de portfólio: cada decisão
precisa ser explicável (problema → solução → alternativas → trade-offs). Nada de CRUD trivial, nada
de complexidade artificial.

**Fase atual: Phase 3 — Catalog concluída; próxima: Phase 4 — Inventory.** Existem a fundação
técnica, `identity` (tenants, usuários, equipes, RBAC, JWT), `suppliers` e `catalog` (produtos e
categorias). Não crie models, endpoints ou telas de fases futuras
(`docs/architecture/overview.md#roadmap`).

**Multi-tenant (ADR-013):** todo model de negócio herda `shared.tenancy.TenantScopedModel`; toda
view de negócio usa `TenantScopedQuerysetMixin`; o tenant vem sempre de `request.user`.

## Stack

| Camada | Tecnologia |
| --- | --- |
| Backend | Python 3.13, Django 5.2 LTS, Django REST Framework, drf-spectacular, SimpleJWT |
| Assíncrono | Celery + RabbitMQ (broker), Celery Beat |
| Dados | PostgreSQL (fonte da verdade), Redis (cache, throttling) |
| Frontend | Vue 3, TypeScript strict, Vite, Vue Router, Pinia, TanStack Query, Axios, vue-i18n, Tailwind CSS v4 (só tokens), Zod, Vitest |
| Tooling | uv, Ruff (lint + format), mypy, pnpm, ESLint, Prettier, vue-tsc |
| Monorepo | Moonrepo v2 (tarefas de engenharia) |
| Runtime local | Docker Compose (infraestrutura e serviços) |
| CI | GitHub Actions executando `moon ci` |

## Arquitetura (resumo)

- **Modular Monolith** (ADR-001). Um deploy Django, módulos de negócio isolados em `backend/apps/`.
- Camadas por módulo, **somente quando a complexidade justificar**:
  `api/` → `application/` → `domain/` ← `infrastructure/`. Módulos simples usam Django idiomático.
- Módulos: `identity`, `customers`, `suppliers`, `catalog`, `inventory`, `orders`, `pricing`,
  `payments`, `shipping`, `notifications`, `audit`. Código transversal em `backend/shared/`.
- Comunicação entre módulos: chamadas à camada `application` do outro módulo (síncrono) ou
  Domain Events (desacoplado). **Nunca** escrever em models de outro módulo diretamente.
- Efeitos secundários (e-mail, notificações, auditoria assíncrona) rodam após o commit, via Celery.

Detalhes: `docs/architecture/overview.md`, `backend.md`, `frontend.md`, `event-driven.md`.

## Estrutura do monorepo

```text
backend/     Django: config/ apps/ shared/ tests/ (uv, pyproject.toml, moon.yml)
frontend/    Vue + TS: src/app src/modules src/components src/services (pnpm, moon.yml)
docs/        architecture/ adr/ domain/ development/ diagrams/
infra/       docker/ (Dockerfiles, nginx.conf)
.moon/       workspace.yml, toolchains.yml
.claude/     agents/ skills/ commands/ rules/ templates/
```

## Comandos

Moonrepo = tarefas de engenharia. Docker Compose = runtime. Makefile = atalhos finos.

```bash
moon run :check            # lint + format-check + typecheck + test (todos os projetos)
moon run :lint | :test | :typecheck | :build
moon run backend:test      # um projeto
moon ci                    # CI: só tarefas afetadas pelas mudanças
docker compose up          # postgres, redis, rabbitmq, backend, frontend, celery
make help                  # atalhos: dev, up, stop, logs, test, lint, check, build, migrate...
```

`backend:test` exige PostgreSQL rodando (`docker compose up -d postgres`). Dentro dos containers,
use `python manage.py ...` (dependências em `/opt/venv`). Detalhes: `docs/architecture/monorepo.md`.

## Regras não negociáveis

1. **Idioma**: código 100% em inglês (classes, variáveis, tabelas, campos, eventos, endpoints,
   arquivos). Comentários podem ser em português. Documentação interna em português. UI em pt-BR
   via i18n. Vocabulário: `docs/domain/glossary.md`.
2. **Regras de negócio pertencem ao backend.** Frontend só antecipa feedback.
3. **API fina**: nada de regra de negócio em views, serializers, permissions ou signals.
4. **Dinheiro**: `Decimal` / `NUMERIC`, nunca `float`. Moeda inicial BRL.
5. **Datas**: timezone-aware, UTC no banco; o frontend converte para o fuso do usuário.
6. **Banco protege invariantes**: FKs, `UNIQUE`, `CHECK`, índices. Não confiar só no código.
7. **Estoque**: `available = on_hand - reserved`; toda mudança gera `StockMovement`; reservas usam
   lock pessimista ordenado (ADR-008). Nunca vender a última unidade duas vezes.
8. **Estados do pedido**: transições somente via máquina de estados do domínio
   (`docs/domain/orders.md`), sempre registrando `OrderStatusHistory`.
9. **Idempotência** em `POST /orders`, `/payments`, `/refunds` via `Idempotency-Key` (ADR-012).
10. **Autorização centralizada** (RBAC por permissões `resource:action`). Proibido
    `if user.role == "ADMIN"` espalhado.
11. **Nunca logar** senha, JWT, dados de cartão ou secrets. Nunca versionar `.env`.
12. **Erros da API** sempre no envelope `{"error": {"code", "message", "details"}}`.

## Princípios de design

- **SOLID pragmático.** SRP é o mais importante: nada de `OrderService` que faz estoque, pagamento,
  e-mail e envio. OCP/Strategy só onde o comportamento realmente varia (pricing, descontos, frete).
  DIP para dependências externas relevantes (`PaymentGateway`, `ShippingProvider`, `EmailProvider`).
- **Patterns com problema declarado**: Strategy (pricing), State (pedido), Adapter (integrações),
  Domain Events/Observer, Repository (só com ganho real), Specification (regras combináveis).
- **Teste anti-overengineering** — antes de criar interface, repository, factory, adapter, base
  class, service, DTO, mapper ou evento: *qual problema concreto isto resolve?* Sem resposta
  objetiva, não crie. Não crie diretórios vazios "para parecer Clean Architecture".
- **Django continua sendo Django.** ORM direto é aceitável em CRUD simples.

## Fluxo obrigatório antes de mudanças relevantes

1. Ler este arquivo → 2. identificar o módulo → 3. ler `docs/domain/<módulo>.md` →
4. ler ADRs relevantes (`docs/adr/README.md`) → 5. mapear impacto → 6. identificar regras
existentes → 7. planejar → 8. implementar → 9. testes → 10. lint/typecheck (`moon run :check`) →
11. revisão de segurança → 12. revisão de arquitetura.

Para mudanças que alterem uma decisão registrada, crie/atualize um ADR (`/create-adr`).

## Testes

pytest + pytest-django + factory_boy + Faker no backend; Vitest no frontend. Pirâmide com maioria
de unit tests. Testes de concorrência e integração rodam contra **PostgreSQL real** (nunca SQLite).
Cenários obrigatórios em `docs/development/testing-strategy.md`.

## Agents, skills e commands

- Agents (`.claude/agents/`): `software-architect`, `backend-engineer`, `frontend-engineer`,
  `database-engineer`, `devops-engineer`, `test-engineer`, `security-reviewer`, `code-reviewer`,
  `ux-reviewer`, `domain-reviewer`.
- Skills (`.claude/skills/`, invocáveis como `/nome`): `create-django-module`,
  `create-rest-endpoint`, `create-domain-event`, `create-celery-task`, `create-vue-feature`,
  `create-database-migration`, `create-moon-task`, `write-unit-tests`, `write-integration-tests`,
  `review-architecture`, `review-security`, `review-domain`, `review-frontend-ux`, `create-adr`.
- Commands (`.claude/commands/`): `/project-status`, `/create-module`, `/create-endpoint`,
  `/create-feature`, `/run-tests`, `/review-code`.
- Rules (`.claude/rules/`) carregam automaticamente conforme os arquivos tocados.
- Templates (`.claude/templates/`) são usados pelas skills.

## Git

Conventional Commits com escopo = módulo: `feat(orders): add stock reservation`. Detalhes em
`docs/development/git-workflow.md`.

## Definition of Done

Quando aplicável: regra implementada no domínio · validação · autorização · testes (incluindo
caminhos de erro) · tratamento de erro padronizado · logs estruturados · migrations · OpenAPI
atualizado · frontend com loading/empty/error states · acessibilidade · revisão de segurança ·
revisão de arquitetura · `moon run :check` verde · documentação/ADR atualizados.
