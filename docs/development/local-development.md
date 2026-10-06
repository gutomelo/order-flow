# Desenvolvimento local


## Pré-requisitos

| Ferramenta | Para quê | Instalação |
| --- | --- | --- |
| Docker + Docker Compose v2 | runtime local (banco, broker, serviços) | docs.docker.com |
| proto + moon v2 | tarefas de engenharia; instala Node/pnpm nas versões fixadas | moonrepo.dev/docs/install |
| uv | Python 3.13 e dependências do backend | docs.astral.sh/uv |
| Git | | |

Node e pnpm **não** precisam ser instalados manualmente: o moon os provisiona conforme
`.moon/toolchains.yml`. O Python é provisionado pelo uv conforme `backend/.python-version`.

## Primeira execução

```bash
git clone <repo> orderflow && cd orderflow
cp .env.example .env              # valores locais; nunca commitar .env
docker compose up                 # postgres, redis, rabbitmq, backend, frontend, celery
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

| Serviço | URL |
| --- | --- |
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api/v1/ |
| OpenAPI (Swagger) | http://localhost:8000/api/docs/ |
| Health | http://localhost:8000/health/ready |
| RabbitMQ management | http://localhost:15672 |
| Flower (opcional) | `docker compose --profile tools up flower` → http://localhost:5555 |

Atalhos: `make dev`, `make stop`, `make logs`, `make migrate`, `make shell`.

### Primeiro acesso

Não há cadastro público de empresas: o operador da plataforma cria a organização e o primeiro ADMIN.

```bash
docker compose exec backend python manage.py create_organization \
  --name "Acme Distribuidora" --admin-email ana@acme.com
# a senha é solicitada no terminal (validadores de senha do Django)
```

Depois, entre em http://localhost:5173 com esse e-mail. O ADMIN cria os demais usuários em
**Usuários**. `createsuperuser` cria um operador da plataforma, que acessa apenas `/admin/`.

## Dois modos de trabalho

**A) Tudo em containers** — `docker compose up`. Mais simples; hot reload via volumes.

**B) Infra em containers, apps nativas** — melhor para debugger e velocidade de testes:

```bash
docker compose up -d postgres redis rabbitmq
moon run backend:dev          # Django em :8000
moon run frontend:dev         # Vite em :5173
cd backend && uv run celery -A config worker -l info   # se precisar de tasks
```

## Tarefas do dia a dia

```bash
moon run :check               # antes de abrir PR: lint + format-check + typecheck + test
moon run :format              # formatar tudo
moon run backend:test         # testes do backend (requer postgres rodando)
moon run frontend:test
moon run :test --affected     # só o que mudou
```

Equivalentes no Makefile: `make check`, `make format`, `make test`, `make lint`, `make build`.

## Dependências

```bash
cd backend && uv add <pacote>            # runtime
cd backend && uv add --dev <pacote>      # desenvolvimento
cd frontend && pnpm add <pacote>
cd frontend && pnpm add -D <pacote>
```

Sempre commitar `uv.lock` / `pnpm-lock.yaml`. Nova dependência relevante: justificar no PR.

## Banco de dados

```bash
make migrate
docker compose exec backend python manage.py makemigrations <module> --name <descricao>
docker compose exec backend python manage.py sqlmigrate <module> <numero>
docker compose exec postgres psql -U orderflow orderflow
```

Reset completo do ambiente local (apaga dados): `docker compose down -v`.

## Variáveis de ambiente

Documentadas em `.env.example`. O Compose funciona sem `.env`; crie-o (`cp .env.example .env`)
para trocar portas do host ou rodar backend/testes nativamente. Grupos: Django (`DJANGO_SECRET_KEY`,
`DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`), banco (`DATABASE_URL`), Redis (`REDIS_URL`), broker
(`CELERY_BROKER_URL`), JWT (tempos de vida), CORS (`CORS_ALLOWED_ORIGINS`), regras de negócio
(`STOCK_RESERVATION_TTL_MINUTES`, `ORDER_PENDING_MAX_AGE_DAYS`), frontend (`VITE_API_BASE_URL`).

## Claude Code neste repositório

- `CLAUDE.md` é carregado automaticamente; `.claude/rules/` carrega regras conforme os arquivos tocados.
- Comandos: `/project-status`, `/create-module`, `/create-endpoint`, `/create-feature`,
  `/run-tests`, `/review-code`.
- Skills invocáveis diretamente: `/create-adr`, `/review-security`, `/review-domain`,
  `/review-architecture`, `/review-frontend-ux`, `/create-moon-task`, entre outras
  (lista completa no `CLAUDE.md`).
- Preferências pessoais: `CLAUDE.local.md` (não versionado).

## Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| Testes do backend falham com erro de conexão | PostgreSQL não está rodando | `docker compose up -d postgres` |
| `moon` reclama de versão | moon fora de `versionConstraint` | `proto install moon` / atualizar |
| Tarefa não reexecuta após mudança | arquivo fora dos `inputs` da tarefa | ajustar `fileGroups` no `moon.yml` |
| Porta em uso | serviço local conflitante | mudar a porta no `.env` (ex.: `POSTGRES_HOST_PORT=15432`) e o `DATABASE_URL` correspondente |
| `backend:test` "passa" sem banco | resultado veio do cache do moon | `moon run backend:test --force` |
| `pnpm add` falha com `MINIMUM_RELEASE_AGE_VIOLATION` | versão publicada há menos de 1 dia | usar a versão anterior |
| Página 404 em HTML no navegador | `DEBUG=True` mostra a página de debug do Django | esperado em dev; com `DEBUG=False` a resposta é JSON |
| `celery-worker` sai com `Connection reset by peer`; RabbitMQ registra `no_exists` (`rabbit_vhost`, `rabbit_runtime_parameters`) mas segue "healthy" | o banco de metadados do RabbitMQ ficou inconsistente (visto após o host suspender com o stack no ar); `rabbitmq-diagnostics ping` não detecta | `docker compose restart rabbitmq`; os serviços Celery têm `restart: unless-stopped` e voltam sozinhos |
