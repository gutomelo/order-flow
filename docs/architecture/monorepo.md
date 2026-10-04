# Monorepo: Moonrepo, Docker Compose e Makefile

Decisões: [ADR-009](../adr/009-moonrepo.md) (Moonrepo) e
[ADR-010](../adr/010-docker-compose-local-environment.md) (Docker Compose).

## Divisão de responsabilidades

```text
                Developer / CI
                      │
        ┌─────────────┼──────────────┐
        ▼             ▼              ▼
     Makefile      Moonrepo     Docker Compose
   (atalhos finos) (tarefas de   (runtime e
        │          engenharia)    infraestrutura)
        └──► delega ──┘              │
                      │              │
           ┌──────────┴───┐   ┌──────┼────────┬──────────┬───────────────┐
           ▼              ▼   ▼      ▼        ▼          ▼               ▼
        backend       frontend  postgres  redis  rabbitmq  backend/frontend  celery-worker/beat
     lint·test·...   lint·test·...
```

| Ferramenta | Responsável por | Não faz |
| --- | --- | --- |
| Moonrepo | lint, format, typecheck, test, build, cache de tarefas, CI seletiva, versões de Node/pnpm | subir banco, broker, containers |
| Docker Compose | PostgreSQL, Redis, RabbitMQ, backend, frontend, Celery worker/beat, Flower | lint/test/build |
| Makefile | atalhos de DX (`make dev`, `make check`) | lógica própria; só delega |
| uv / pnpm | dependências de cada stack | coordenação entre projetos |

## Versão e arquivos do Moonrepo

O projeto usa **moon v2** (validado contra a documentação oficial em 2026-10, versão 2.5.x).
Mudanças relevantes em relação ao v1 que afetam este repositório:

| v1 | v2 (usado aqui) |
| --- | --- |
| `.moon/toolchain.yml` | `.moon/toolchains.yml` |
| `python:` no toolchain | `unstable_python` / `unstable_uv` (experimental — **não usamos**) |
| `tasks.*.platform` / `toolchain` | `tasks.*.toolchains`, `toolchains.default` no projeto |
| `inferInputs: true` | `inferInputs: false` (inputs explícitos obrigatórios para cache correto) |
| `tasks.*.local: true` | `tasks.*.preset: 'server'` |
| `moon run test` encontra o projeto mais próximo | usar `~:test` para isso |

Arquivos:

| Arquivo | Estado | Conteúdo |
| --- | --- | --- |
| `.moon/workspace.yml` | criado (Phase 0) | projetos `backend`/`frontend`, VCS `git`/`master`, `versionConstraint` |
| `.moon/toolchains.yml` | criado (Phase 0) | `javascript` (pnpm), `node`, `pnpm` com versões fixadas |
| `backend/moon.yml` | Phase 1 (plano abaixo) | tarefas Python via `uv` |
| `frontend/moon.yml` | Phase 1 (plano abaixo) | tarefas TypeScript/Vue |

> Até a Phase 1 criar `backend/` e `frontend/`, comandos `moon` falham por projetos inexistentes.
> Isso é esperado.

Esquemas JSON para validação no editor: `moon sync config-schemas` gera `.moon/cache/schemas/`
(referenciados por `$schema` no topo de cada arquivo).

## Tarefas padronizadas

| Tarefa | Backend | Frontend | Cache | CI |
| --- | --- | --- | --- | --- |
| `install` | `uv sync --locked` | (automático pelo toolchain JS) | não | sim |
| `lint` | `ruff check` + `lint-imports` | `eslint` | sim | sim |
| `format` | `ruff format` | `prettier --write` | não | não |
| `format-check` | `ruff format --check` | `prettier --check` | sim | sim |
| `typecheck` | `mypy` | `vue-tsc --build` | sim | sim |
| `test` | `pytest` | `vitest run` | sim | sim |
| `check` | agrega lint, format-check, typecheck, test | idem | — | sim |
| `build` | `manage.py check` + migrations sincronizadas (após `check`) | `vite build` (após `typecheck`) | sim | sim |
| `dev` | `runserver` | `vite` | não (`server`) | não |

Comandos globais:

```bash
moon run :lint          # lint em todos os projetos que têm a tarefa
moon run :typecheck
moon run :test
moon run :check         # tudo
moon run :build
moon run backend:test   # um projeto
moon run :test --affected   # só projetos afetados pelas mudanças locais
moon ci                 # CI: afetados + runInCI, continua após falhas e gera relatório
```

### Grafo de dependências entre tarefas

```mermaid
flowchart LR
    subgraph backend
      bi[install] --> bl[lint]
      bi --> bf[format-check]
      bi --> bt[typecheck]
      bi --> bte[test]
      bl --> bc[check]
      bf --> bc
      bt --> bc
      bte --> bc
      bc --> bb[build]
    end
    subgraph frontend
      fl[lint] --> fc[check]
      ff[format-check] --> fc
      ft[typecheck] --> fc
      ft --> fte[test]
      fte --> fc
      ft --> fb[build]
    end
```

`frontend:test` depende de `typecheck` (erros de tipo falham antes e mais barato que os testes).
`backend:build` depende de `backend:check` (não "empacotamos" backend que não passou nas verificações).

## Plano: `backend/moon.yml` (Phase 1)

```yaml
$schema: '../.moon/cache/schemas/project.json'

language: 'python'
layer: 'application'
stack: 'backend'
tags: ['python', 'django']

project:
  title: 'OrderFlow API'
  description: 'Django REST API (modular monolith) and Celery workers.'

# Toolchain Python do moon v2 é experimental; uv cuida de Python e dependências.
toolchains:
  default: 'system'

fileGroups:
  sources:
    - 'apps/**/*.py'
    - 'config/**/*.py'
    - 'shared/**/*.py'
    - 'manage.py'
  tests:
    - 'tests/**/*.py'
    - 'conftest.py'
  configs:
    - 'pyproject.toml'
    - 'uv.lock'
    - '.python-version'
  migrations:
    - 'apps/**/migrations/*.py'

tasks:
  install:
    command: 'uv sync --locked'
    inputs:
      - '@group(configs)'
    options:
      cache: false

  lint:
    script: 'uv run ruff check . && uv run lint-imports'
    deps: ['~:install']
    inputs:
      - '@group(sources)'
      - '@group(tests)'
      - '@group(configs)'

  format:
    command: 'uv run ruff format .'
    deps: ['~:install']
    options:
      cache: false
      runInCI: false

  format-check:
    command: 'uv run ruff format --check .'
    deps: ['~:install']
    inputs:
      - '@group(sources)'
      - '@group(tests)'
      - '@group(configs)'

  typecheck:
    command: 'uv run mypy .'
    deps: ['~:install']
    inputs:
      - '@group(sources)'
      - '@group(tests)'
      - '@group(configs)'

  test:
    command: 'uv run pytest'
    deps: ['~:install']
    env:
      DJANGO_SETTINGS_MODULE: 'config.settings.test'
    inputs:
      - '@group(sources)'
      - '@group(tests)'
      - '@group(configs)'

  check:
    command: 'echo backend checks passed'
    deps: ['~:lint', '~:format-check', '~:typecheck', '~:test']
    options:
      cache: false

  build:
    script: 'uv run python manage.py check && uv run python manage.py makemigrations --check --dry-run'
    deps: ['~:check']
    env:
      DJANGO_SETTINGS_MODULE: 'config.settings.test'
    inputs:
      - '@group(sources)'
      - '@group(migrations)'
      - '@group(configs)'

  dev:
    command: 'uv run python manage.py runserver 0.0.0.0:8000'
    preset: 'server'
```

Notas:

- `check` usa um `echo` porque a documentação do moon v2 não documenta tarefas sem comando; a tarefa
  existe para agregar `deps` sob um nome único.
- `test` precisa de PostgreSQL acessível (variáveis `DATABASE_URL` etc. vindas do ambiente).
  Localmente: `docker compose up -d postgres redis rabbitmq`. Na CI: service containers.
- O "artefato" de deploy do backend é a imagem Docker, construída em job próprio da CI (fora do moon).

## Plano: `frontend/moon.yml` (Phase 1)

```yaml
$schema: '../.moon/cache/schemas/project.json'

language: 'typescript'
layer: 'application'
stack: 'frontend'
tags: ['vue', 'typescript']

project:
  title: 'OrderFlow Web'
  description: 'Vue 3 + TypeScript SPA for the OrderFlow B2B platform.'

fileGroups:
  sources:
    - 'src/**/*'
    - 'index.html'
    - 'public/**/*'
  tests:
    - 'src/**/*.spec.ts'
    - 'src/**/*.test.ts'
  configs:
    - 'package.json'
    - 'pnpm-lock.yaml'
    - 'tsconfig*.json'
    - 'vite.config.ts'
    - 'vitest.config.ts'
    - 'eslint.config.*'
    - '.prettierrc*'

tasks:
  lint:
    command: 'pnpm exec eslint .'
    inputs:
      - '@group(sources)'
      - '@group(configs)'

  format:
    command: 'pnpm exec prettier --write .'
    options:
      cache: false
      runInCI: false

  format-check:
    command: 'pnpm exec prettier --check .'
    inputs:
      - '@group(sources)'
      - '@group(configs)'

  typecheck:
    command: 'pnpm exec vue-tsc --build'
    inputs:
      - '@group(sources)'
      - '@group(configs)'

  test:
    command: 'pnpm exec vitest run'
    deps: ['~:typecheck']
    inputs:
      - '@group(sources)'
      - '@group(configs)'

  check:
    command: 'echo frontend checks passed'
    deps: ['~:lint', '~:format-check', '~:typecheck', '~:test']
    options:
      cache: false

  build:
    command: 'pnpm exec vite build'
    deps: ['~:typecheck']
    inputs:
      - '@group(sources)'
      - '@group(configs)'
    outputs:
      - 'dist/**/*'

  dev:
    command: 'pnpm exec vite --host 0.0.0.0'
    preset: 'server'
```

A tarefa `generate-api-types` (OpenAPI → TypeScript) entra na Phase 2 via skill `create-moon-task`.

### Validação já feita (Phase 0)

Os dois planos acima, junto com `.moon/workspace.yml` e `.moon/toolchains.yml`, foram carregados
pelo **moon 2.5.6** em um workspace temporário (`moon query projects` e `moon task` para cada
tarefa). Resultado: configuração aceita sem erros; backend resolvido com toolchain `system`;
frontend com `javascript`, `node` e `pnpm` detectados automaticamente; `deps`, `runInCI` e
`preset: 'server'` resolvidos como esperado. Tarefas sem `inputs` (ex.: `check`) passam a
considerar todo o projeto (`<projeto>/**/*`) como input.

### Pontos a validar na Phase 1 (execução real)

- Instalação de dependências do frontend sem `package.json` na raiz (projeto JS isolado).
- Comportamento do cache de `test` do backend (dependência de serviços externos não é input).
- Versões fixadas em `.moon/toolchains.yml` (Node 24 LTS, pnpm) compatíveis com as dependências.

## CI (GitHub Actions) — plano

```yaml
name: CI

on:
  push:
    branches: ['master']
  pull_request:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: orderflow
          POSTGRES_PASSWORD: orderflow
          POSTGRES_DB: orderflow
        ports: ['5432:5432']
        options: >-
          --health-cmd "pg_isready -U orderflow"
          --health-interval 5s --health-timeout 5s --health-retries 10
      redis:
        image: redis:7
        ports: ['6379:6379']
    env:
      DATABASE_URL: postgres://orderflow:orderflow@localhost:5432/orderflow
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # necessário para detectar arquivos afetados
          filter: 'blob:none'
      - uses: astral-sh/setup-uv@v6   # fixar a major vigente na Phase 1
      - uses: moonrepo/setup-toolchain@v0
      - run: moon ci
```

- `moon ci` executa apenas tarefas **afetadas** pelas mudanças (PR: comparação com `master`) e
  respeita `runInCI` (`format` e `dev` ficam fora). Mudança só no frontend não executa tarefas
  do backend.
- Confiabilidade acima de otimização: alterações em arquivos de configuração compartilhados
  (`.moon/**`, workflow) devem disparar tudo; um job agendado (nightly) roda `moon run :check`
  completo, sem filtro de afetados.
- Relatório `.moon/cache/ciReport.json` publicado como artifact do job.
- Job separado (Phase 1+) constrói as imagens Docker para validar os Dockerfiles.
- Cache remoto de tarefas do moon (`remote` no workspace) é evolução futura, não necessário agora.

## Docker Compose — plano

```text
services:
  postgres        postgres:17, volume nomeado, healthcheck pg_isready
  redis           redis:7, healthcheck redis-cli ping
  rabbitmq        rabbitmq:4-management, healthcheck rabbitmq-diagnostics ping
  backend         build infra/docker/backend.Dockerfile, runserver, depends_on (healthy)
  celery-worker   mesma imagem, `celery -A config worker -Q default,notifications,integrations,maintenance`
  celery-beat     mesma imagem, `celery -A config beat`
  frontend        build infra/docker/frontend.Dockerfile, vite dev server
  flower          profile "tools", opcional
```

Versões exatas das imagens fixadas na Phase 1.

## Makefile — plano

```makefile
.PHONY: dev stop logs ps test lint typecheck check build format migrate shell

dev:        ## sobe o ambiente completo
	docker compose up
stop:
	docker compose down
logs:
	docker compose logs -f
ps:
	docker compose ps
test:
	moon run :test
lint:
	moon run :lint
typecheck:
	moon run :typecheck
check:
	moon run :check
build:
	moon run :build
format:
	moon run :format
migrate:
	docker compose exec backend uv run python manage.py migrate
shell:
	docker compose exec backend uv run python manage.py shell
```

O Makefile não contém lógica de pipeline: cada alvo é uma linha que delega.
