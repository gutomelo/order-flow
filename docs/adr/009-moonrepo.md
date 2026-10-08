# ADR-009: Moonrepo como coordenador do monorepo poliglota

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-010, `docs/architecture/monorepo.md`

## Context

Backend em Python (uv, Ruff, mypy, pytest) e frontend em TypeScript (pnpm, ESLint, Prettier,
vue-tsc, Vitest) vivem no mesmo repositório. Precisamos padronizar como lint, formatação,
type-check, testes e build são executados — localmente e na CI — com:
- mesma interface de comando para as duas stacks (`<projeto>:<tarefa>`);
- dependências entre tarefas (ex.: `build` só após `typecheck`);
- cache: não reexecutar o que não mudou;
- execução seletiva na CI: mudança só no frontend não roda a suíte do backend;
- versões de ferramentas consistentes entre máquinas.

## Decision

Usar **Moonrepo v2** como coordenador de tarefas de engenharia:

- `.moon/workspace.yml` declara os projetos `backend` e `frontend` e o VCS (`master`).
- `.moon/toolchains.yml` habilita o toolchain JavaScript (Node + pnpm com versões fixadas, instaladas
  via proto). Para Python, o toolchain do moon v2 ainda é experimental (`unstable_python`); por isso
  as tarefas do backend usam o toolchain `system` e delegam ao **uv**, que já fixa a versão do Python
  e as dependências.
- Cada projeto tem `moon.yml` com tarefas de nomes padronizados: `lint`, `format`, `format-check`,
  `typecheck`, `test`, `check`, `build`, `dev`. `moon run :check` roda tudo em todos os projetos.
- Toda tarefa cacheável declara `inputs` (o v2 não infere inputs), garantindo cache correto.
- CI executa `moon ci`, que roda apenas tarefas afetadas pelas mudanças (com `fetch-depth: 0`).
- Moonrepo **não** gerencia infraestrutura: containers são responsabilidade do Docker Compose
  (ADR-010). O Makefile é uma camada fina sobre ambos.

## Alternatives Considered

### Makefile somente

- Prós: zero dependências, universal.
- Contras: sem cache por hash de inputs, sem grafo de dependências entre projetos, sem detecção de
  afetados; CI seletiva vira script caseiro.
- Por que não: resolve a interface de comando, mas não cache nem seletividade.

### Nx

- Prós: muito completo, cache e affected maduros.
- Contras: centrado em JavaScript; suporte a Python via plugins da comunidade; configuração pesada.

### Turborepo

- Prós: simples, cache bom.
- Contras: modelado sobre workspaces de package managers JS; projetos Python ficam de fora ou
  exigem `package.json` artificial.

### Scripts customizados (bash/Python)

- Contras: reimplementar cache, grafo e affected; manutenção contínua; sem valor de portfólio.

## Consequences

### Positivas

- Interface única e previsível para as duas stacks; mesmos comandos na máquina e na CI.
- Cache por hash de inputs e execução apenas do que foi afetado.
- Versões de Node/pnpm garantidas pelo toolchain.

### Negativas / custos aceitos

- Curva de aprendizado e mais um arquivo de configuração por projeto.
- O moon v2 introduziu mudanças de configuração (ex.: `toolchains.yml`, `inferInputs: false`);
  documentação desatualizada na internet pode confundir — sempre validar na doc oficial.
- Python não usa o toolchain nativo do moon: a versão do Python é garantida pelo uv, não pelo moon.
- Testes do backend dependem de PostgreSQL rodando (serviço externo ao moon): localmente via
  Docker Compose, na CI via service containers.

### Quando revisitar

Quando o toolchain Python do moon sair de `unstable_` (avaliar migrar o backend para ele), ou se o
custo de manutenção da configuração superar o ganho de cache/seletividade.
