---
description: Executa os testes do OrderFlow via Moonrepo (todos, por projeto ou só os afetados) e resume falhas com causa provável.
argument-hint: [all | backend | frontend | affected | caminho/do/teste]
disable-model-invocation: true
---

# Executar testes: $ARGUMENTS

Escolha o comando conforme o argumento:

| Argumento | Comando |
| --- | --- |
| vazio ou `all` | `moon run :test` |
| `backend` | `moon run backend:test` |
| `frontend` | `moon run frontend:test` |
| `affected` | `moon run :test --affected` |
| caminho `backend/...` | `cd backend && uv run pytest <caminho>` |
| caminho `frontend/...` | `cd frontend && pnpm exec vitest run <caminho>` |

Pré-requisito do backend: PostgreSQL (e Redis/RabbitMQ quando o teste usar) rodando —
`docker compose up -d postgres redis rabbitmq`. Se a conexão falhar, informe isso em vez de
diagnosticar como bug de código.

Ao final, reporte:
- totais (passou/falhou/pulou);
- para cada falha: teste, mensagem principal, causa provável e arquivo:linha suspeito;
- não altere código para "fazer passar" sem o usuário pedir — proponha a correção.
