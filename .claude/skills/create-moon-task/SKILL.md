---
name: create-moon-task
description: Adiciona ou altera uma tarefa do Moonrepo v2 (moon.yml) no OrderFlow com inputs explícitos, dependências, cache e comportamento em CI corretos, validando a sintaxe na documentação oficial. Use ao criar tarefas de lint, test, build, geração de código ou utilitários.
argument-hint: <project> <task-name> [o que a tarefa faz]
---

# Criar tarefa Moonrepo

Entrada: `$ARGUMENTS`

## 1. Justificar

- A tarefa é de **engenharia** (lint, test, build, geração de código, verificação)? Infraestrutura
  e runtime ficam no Docker Compose, não no moon.
- Já existe tarefa equivalente? Os nomes padrão são `lint`, `format`, `format-check`, `typecheck`,
  `test`, `check`, `build`, `dev`.

## 2. Validar sintaxe

O projeto usa **moon v2** (ver `.moon/workspace.yml`). Para qualquer propriedade fora de
`.claude/templates/moon-task.md`, consulte a documentação (Context7 `/websites/moonrepo_dev` ou
https://moonrepo.dev/docs/config/project). **Não invente chaves.**

## 3. Escrever a tarefa

- `command` para um único comando; `script` para pipes, `&&` ou redirecionamentos.
- `inputs` obrigatórios para tarefas cacheáveis (v2 não infere inputs). Prefira `@group(...)`.
- `outputs` somente se gerar artefatos.
- `deps` para ordem (`~:typecheck`), `options.cache: false` para efeitos colaterais,
  `preset: 'server'` para processos longos, `options.runInCI` quando não deve rodar em CI.
- Backend: `uv run ...` (toolchain `system`). Frontend: binários do `node_modules`.
- Se for uma etapa de `check`, adicione-a às `deps` da tarefa `check` do projeto.

## 4. Verificar e documentar

```bash
moon task <project>:<task>      # mostra a configuração resolvida
moon run <project>:<task>
moon run <project>:<task>       # 2ª execução deve vir do cache (se cacheável)
```

Atualize a tabela de tarefas em `docs/architecture/monorepo.md` e, se útil, o `Makefile`.
