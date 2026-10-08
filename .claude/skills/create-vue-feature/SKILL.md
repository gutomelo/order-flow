---
name: create-vue-feature
description: Cria uma feature do frontend OrderFlow em src/modules/<feature> com API tipada, TanStack Query para server state, formulários com Zod, rotas lazy, i18n pt-BR, estados de loading/empty/error e testes Vitest. Use ao criar telas como pedidos, produtos, clientes e estoque.
argument-hint: <feature-name> [descrição das telas]
arguments: [feature]
---

# Criar feature Vue: `$feature`

## 1. Contexto

- Leia `docs/architecture/frontend.md` e o contrato dos endpoints do backend (OpenAPI ou serializers).
- Verifique componentes reutilizáveis existentes (`src/components/`): `DataTable`, `StatusBadge`,
  `EmptyState`, `ConfirmDialog`, `PageHeader`, campos de formulário. Reutilize antes de criar.

## 2. Estrutura

Siga `.claude/templates/vue-feature.md`. Crie apenas as pastas que a feature usa.

## 3. Implementação (nesta ordem)

1. `types/` — tipos derivados do contrato da API (dinheiro como `string` decimal, datas ISO UTC).
2. `api/` — funções usando o cliente HTTP compartilhado (`src/services/http`).
3. `composables/` — query keys centralizadas, `useQuery`/`useMutation` com invalidação explícita.
4. `schemas/` — Zod para formulários; mensagens via i18n.
5. `pages/` e `components/` — páginas consomem composables; componentes de apresentação recebem props.
6. `routes.ts` — rotas lazy com `meta` de permissão (para UX; o backend é a autoridade).
7. Textos em `src/app/i18n/locales/pt-BR` (chaves em inglês: `orders.list.emptyTitle`).

## 4. UX obrigatória

Loading (skeleton), empty state com próximo passo, error state com "tentar novamente", feedback de
sucesso, confirmação em ações destrutivas, anti double-submit, acessibilidade por teclado,
status com ícone + texto, apenas tokens semânticos de cor.

## 5. Testes e verificação

Vitest para composables, schemas e componentes com lógica. `moon run frontend:check`.
Depois rode a skill `review-frontend-ux`.
