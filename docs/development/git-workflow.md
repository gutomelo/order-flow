# Fluxo de Git

## Branches

- `master`: sempre verde (CI passando), deployável.
- Trabalho em branches curtas a partir de `master`: `<type>/<escopo>-<descricao-curta>`
  — `feat/orders-stock-reservation`, `fix/inventory-negative-availability`, `docs/adr-outbox`.
- Merge via Pull Request com CI verde. Preferência por **squash merge** com mensagem em
  Conventional Commits (histórico linear e legível).

## Conventional Commits

```text
<type>(<scope>): <descrição no imperativo, minúscula, sem ponto final>

[corpo opcional: o porquê da mudança]

[rodapé opcional: BREAKING CHANGE: ..., Refs: #123]
```

| Tipo | Uso |
| --- | --- |
| `feat` | nova funcionalidade |
| `fix` | correção de bug |
| `refactor` | mudança interna sem alterar comportamento |
| `test` | testes |
| `docs` | documentação, ADRs |
| `perf` | performance |
| `build` | dependências, Docker, empacotamento |
| `ci` | pipelines |
| `chore` | manutenção sem impacto em código de produção |
| `style` | formatação sem mudança de lógica |

Escopos: nomes dos módulos (`orders`, `inventory`, `payments`, `identity`, ...), `frontend`,
`backend`, `shared`, `architecture`, `moon`, `docker`, `ci`, `claude` (context engineering).

Exemplos:

```text
feat(orders): add stock reservation
fix(inventory): prevent negative availability
refactor(payments): extract payment gateway
test(orders): add concurrent order scenario
docs(architecture): add stock locking ADR
ci(moon): run affected tasks on pull requests
```

## Pull Requests

- Template: `.claude/templates/pull-request.md` (o que muda, por quê, decisões, como testar,
  checklist da Definition of Done).
- PR pequeno e focado; mudanças de comportamento acompanhadas de testes e docs de domínio.
- Revisão automatizada com `/review-code` antes de pedir revisão humana.
- Mudança de decisão arquitetural ⇒ ADR no mesmo PR.

## Hooks

`pre-commit` executa verificações rápidas (Ruff, Prettier, detecção de chaves privadas). Testes e
type-check completos rodam via `moon run :check` e na CI.

## O que nunca versionar

`.env`, credenciais, dumps de banco, `CLAUDE.local.md`, `.claude/settings.local.json`,
`.moon/cache/`, `node_modules/`, `.venv/` (ver `.gitignore`).
