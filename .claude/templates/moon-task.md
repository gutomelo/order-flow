# Template: tarefa Moonrepo (v2)

Sintaxe validada contra https://moonrepo.dev/docs/config/project (moon v2.5.x).
**Antes de usar uma propriedade fora deste template, confirme na documentação oficial.**

## Tarefa cacheável (lint/test/typecheck/build)

```yaml
tasks:
  <name>:
    command: '<binário> <args>'      # um único comando; pipes/&&/redirect → use `script`
    inputs:                          # obrigatório: v2 não infere inputs (inferInputs: false)
      - '@group(sources)'
      - '@group(configs)'
    outputs:                         # apenas se gerar artefatos (ex.: dist/**/*)
      - 'dist/**/*'
    deps:
      - '~:<outra-tarefa-do-projeto>'
```

## Tarefa backend (Python via uv)

O projeto `backend` define `toolchains: { default: 'system' }`, então os comandos rodam do PATH:

```yaml
tasks:
  <name>:
    command: 'uv run <ferramenta> <args>'
    inputs:
      - '@group(sources)'
      - '@group(configs)'
```

## Servidor / processo longo

```yaml
tasks:
  dev:
    command: 'vite'
    preset: 'server'     # cache off, persistent, não roda em CI
```

## Tarefa utilitária sem cache

```yaml
tasks:
  install:
    command: 'uv sync --locked'
    inputs:
      - 'pyproject.toml'
      - 'uv.lock'
    options:
      cache: false
```

## Opções úteis (`options`)

| Opção | Valores | Uso |
| --- | --- | --- |
| `cache` | `true`, `false`, `'local'`, `'remote'` | desligar para tarefas com efeitos colaterais |
| `runInCI` | `true`/`'affected'`, `'always'`, `false`, `'only'` | controlar execução no `moon ci` |
| `runDepsInParallel` | `true`/`false` | `false` para deps em ordem |
| `outputStyle` | `'stream'`, `'buffer'`, `'hash'`, `'none'` | saída no terminal |
| `runFromWorkspaceRoot` | `true`/`false` | executar a partir da raiz do repo |

## Convenção de nomes

`lint`, `format`, `format-check`, `typecheck`, `test`, `check`, `build`, `dev`. Nome novo só se
nenhum destes servir; documente em `docs/architecture/monorepo.md`.
