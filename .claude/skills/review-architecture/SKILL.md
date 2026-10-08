---
name: review-architecture
description: Revisa a arquitetura das mudanças atuais (ou de um módulo) no OrderFlow — fronteiras entre módulos, direção das dependências, camadas, acoplamento, god classes, abstrações sem problema concreto e aderência aos ADRs. Use após mudanças estruturais ou antes de abrir PR de uma feature relevante.
argument-hint: [escopo: módulo, caminho ou "diff"]
context: fork
agent: software-architect
---

# Revisão de arquitetura

Escopo: `$ARGUMENTS` (se vazio, revise o diff da branch atual contra `master`).

1. Leia `CLAUDE.md`, `.claude/rules/architecture.md`, `docs/architecture/overview.md`,
   `docs/architecture/backend.md` (ou `frontend.md`) e os ADRs relacionados ao escopo.
2. Levante as mudanças: `git diff master...HEAD --stat` e `git diff master...HEAD` (ou leia o
   módulo/caminho indicado).
3. Verifique:
   - imports entre módulos respeitam as fronteiras (sem escrita em models de outro módulo, sem
     importar `infrastructure`/`api` alheios); rode `cd backend && uv run lint-imports` se existir;
   - direção das camadas `api → application → domain`, `infrastructure` implementando portas;
   - views/serializers/signals/tasks sem regra de negócio;
   - responsabilidades: classes/use cases com mais de uma intenção de negócio;
   - abstrações (interface, repository, factory, base class, DTO, mapper) **com** problema concreto;
   - decisões que contradizem ADRs ou que deveriam gerar um ADR novo.
4. Gere o relatório no formato de `.claude/templates/review-report.md`, ordenado por severidade, com
   recomendação clara e trade-offs. Indique explicitamente se algum ADR precisa ser criado.
