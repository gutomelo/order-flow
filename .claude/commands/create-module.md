---
description: Fluxo completo para iniciar um módulo de negócio do backend (planejamento, revisão arquitetural, criação via skill create-django-module, documento de domínio e verificação).
argument-hint: <module-name>
disable-model-invocation: true
---

# Criar módulo: $ARGUMENTS

Siga o fluxo obrigatório do `CLAUDE.md`:

1. **Contexto**: leia `CLAUDE.md`, `docs/architecture/backend.md`, `docs/architecture/domain-model.md`
   e `docs/domain/$ARGUMENTS.md` (se existir).
2. **Fase**: confirme no roadmap (`docs/architecture/overview.md`) que este módulo pertence à fase
   atual. Se não pertencer, avise o usuário e pergunte antes de continuar.
3. **Fronteiras**: delegue ao agent `software-architect` a validação de responsabilidades, dados
   próprios, dependências permitidas e nível de estrutura (`simple` ou `rich`).
4. **Plano**: apresente ao usuário entidades, invariantes, use cases, eventos, permissões e endpoints
   previstos. Aguarde confirmação se houver decisão de negócio em aberto.
5. **Criação**: use a skill `create-django-module` com o nível decidido.
6. **Documento de domínio**: preencha `docs/domain/$ARGUMENTS.md` (template
   `.claude/templates/domain-doc.md`) e atualize `docs/domain/glossary.md`.
7. **Verificação**: `moon run backend:check`.
8. **Resumo**: estrutura criada, decisões e próximos passos (endpoints, testes, frontend).
