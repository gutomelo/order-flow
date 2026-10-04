---
description: Fluxo completo para entregar uma feature de ponta a ponta (backend + frontend) seguindo a Definition of Done do OrderFlow.
argument-hint: <descrição da feature>
disable-model-invocation: true
---

# Criar feature: $ARGUMENTS

Execute o fluxo de 12 passos do `CLAUDE.md`:

1. Ler `CLAUDE.md`.
2. Identificar módulo(s) afetado(s) — backend e frontend.
3. Consultar `docs/domain/` dos módulos.
4. Consultar ADRs relevantes (`docs/adr/README.md`).
5. Mapear impacto: models, migrations, use cases, eventos, tasks, endpoints, permissões, telas.
6. Identificar regras existentes que serão reutilizadas ou alteradas.
7. **Planejar** e apresentar o plano ao usuário (com decisões em aberto) antes de implementar.
8. Implementar:
   - backend: domínio → application → persistência (`create-database-migration`) → API
     (`create-rest-endpoint`) → eventos/tasks (`create-domain-event`, `create-celery-task`);
   - frontend: `create-vue-feature`.
9. Testes: `write-unit-tests` e `write-integration-tests`.
10. `moon run :check`.
11. Revisão de segurança: skill `review-security`.
12. Revisão de arquitetura e domínio: skills `review-architecture` e `review-domain`; UX:
    `review-frontend-ux`.

Ao final, apresente o checklist da Definition of Done (`CLAUDE.md`) marcado item a item, com
justificativa para itens não aplicáveis, e sugira a mensagem de commit em Conventional Commits.
