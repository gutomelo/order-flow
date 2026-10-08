---
paths:
  - ".moon/**"
  - "**/moon.yml"
  - "docker-compose*.yml"
  - "infra/**"
  - ".github/**"
  - "Makefile"
---

# Moonrepo, Docker Compose, CI

- **Moon = tarefas de engenharia** (lint, format, typecheck, test, build, CI).
  **Docker Compose = runtime** (postgres, redis, rabbitmq, backend, frontend, celery).
  **Makefile = atalhos finos** que delegam para moon/compose. Nenhum duplica a lógica do outro.
- Moon é **v2**: arquivos `.moon/workspace.yml`, `.moon/toolchains.yml` (plural), `moon.yml` por
  projeto. Antes de adicionar qualquer propriedade, confirme na documentação oficial
  (moonrepo.dev/docs) ou via Context7 — não invente chaves.
- Em v2, `inferInputs` é `false` por padrão: **toda tarefa cacheável declara `inputs`**
  (preferir `fileGroups`). Tarefas com efeitos colaterais ou servidores usam `options.cache: false`
  ou `preset: 'server'`.
- Backend usa toolchain `system` + `uv run ...` (toolchain Python do moon ainda é `unstable_`).
- Nomes de tarefas padronizados em todos os projetos: `lint`, `format`, `format-check`,
  `typecheck`, `test`, `check`, `build`, `dev`.
- Comandos com pipes/redirecionamentos/múltiplos comandos usam `script`, não `command`.
- Docker: imagens com usuário não-root, healthchecks em todos os serviços de infraestrutura,
  `depends_on` com `condition: service_healthy`, sem secrets em `Dockerfile`.
- CI: GitHub Actions com `moonrepo/setup-toolchain`, checkout com `fetch-depth: 0` (necessário
  para detecção de arquivos afetados) e `moon ci`.
