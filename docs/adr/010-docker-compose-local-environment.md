# ADR-010: Docker Compose para o ambiente local

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-004, ADR-005, ADR-006, ADR-009, `docs/development/local-development.md`

## Context

O sistema depende de PostgreSQL, Redis e RabbitMQ, além do próprio backend, do worker Celery, do
Celery Beat e do frontend. Instalar e versionar esses serviços manualmente em cada máquina gera
divergência ("funciona na minha máquina") e um onboarding lento. Para portfólio, qualquer pessoa
deve conseguir rodar o sistema com um comando.

## Decision

Usar **Docker Compose** como runtime local, com um `docker-compose.yml` na raiz contendo:

| Serviço | Papel |
| --- | --- |
| `postgres` | banco principal (volume nomeado, healthcheck `pg_isready`) |
| `redis` | cache/throttling (healthcheck `redis-cli ping`) |
| `rabbitmq` | broker (imagem com management UI, healthcheck) |
| `backend` | Django (runserver em dev), depende de postgres/redis/rabbitmq saudáveis |
| `celery-worker` | worker Celery (mesma imagem do backend) |
| `celery-beat` | agendador (mesma imagem) |
| `frontend` | Vite dev server |
| `flower` | opcional (profile `tools`) |

Diretrizes: imagens com versão fixada; `depends_on` com `condition: service_healthy`; código montado
como volume para hot reload; variáveis via `.env` (com `.env.example` versionado); usuário não-root
nas imagens próprias; Dockerfiles em `infra/docker/`.

Divisão de responsabilidades: **Compose = runtime**, **Moon = tarefas de engenharia** (ADR-009).
O desenvolvedor pode rodar apenas a infraestrutura (`docker compose up -d postgres redis rabbitmq`)
e executar backend/frontend/testes nativamente via moon.

## Alternatives Considered

### Instalação nativa dos serviços

- Contras: versões divergentes, onboarding lento, difícil de reproduzir a CI.

### Kubernetes local (kind/minikube/Tilt)

- Contras: complexidade operacional desproporcional para desenvolvimento de um monolito.

### Dev Containers

- Prós: ambiente de edição padronizado.
- Contras: acopla ao editor; pode ser adicionado depois sobre o mesmo Compose.

## Consequences

### Positivas

- `docker compose up` sobe um ambiente funcional; paridade com a CI (mesmas versões de serviços).

### Negativas / custos aceitos

- Requer Docker; consumo de memória maior; hot reload via volume pode ser mais lento em macOS/Windows.

### Quando revisitar

Se o projeto ganhar ambiente de staging/produção containerizado que justifique alinhar a
orquestração local à de produção.
