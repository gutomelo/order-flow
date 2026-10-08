# ADR-003: Vue 3 + TypeScript no frontend, TanStack Query para server state

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-007, `docs/architecture/frontend.md`

## Context

O frontend é um painel B2B denso em dados: tabelas paginadas com filtros, formulários com validação,
dashboards e muitas mutações (criar pedido, cancelar, pagar, ajustar estoque). Dois problemas
recorrentes nesse tipo de aplicação:
1. **Server state tratado como client state** — dados remotos copiados para stores globais ficam
   desatualizados, exigem invalidação manual e duplicam lógica de loading/erro.
2. **Contrato frágil com a API** — tipos divergentes do backend geram erros em runtime.

## Decision

- **Vue 3** com Composition API (`<script setup lang="ts">`), **TypeScript strict**, **Vite**,
  **Vue Router**, **Vitest**, **pnpm**.
- **TanStack Query for Vue** para todo server state (cache, revalidação, invalidação após mutation,
  estados de loading/erro padronizados).
- **Pinia** apenas para client state: sessão/usuário atual, preferências, UI global.
- **Axios** como cliente HTTP único, com interceptors de autenticação, `Idempotency-Key` e
  normalização do envelope de erro.
- **Zod** para schemas de formulário (validação client-side apenas como feedback antecipado).
- Tipos da API gerados a partir do OpenAPI do backend (ferramenta definida na Phase 2, ex.:
  `openapi-typescript`).
- **vue-i18n** com `pt-BR` desde o início.
- Componentes acessíveis construídos sobre primitivas headless; estilos via design tokens
  (escolha da biblioteca de primitivas e utilitários CSS na Phase 1, registrada em
  `docs/architecture/frontend.md`).

## Alternatives Considered

### React + TypeScript

- Prós: ecossistema maior.
- Contras: nenhum ganho específico para este domínio; mais decisões (roteamento, formulários).
- Por que não: Vue atende igualmente e é requisito do projeto; Composition API + TS é maduro.

### Somente Pinia para dados remotos

- Prós: uma única ferramenta.
- Contras: reimplementar cache, deduplicação, revalidação e invalidação; dados obsoletos.
- Por que não: é exatamente o problema 1.

### VeeValidate/Yup ou validação manual

- Por que não Yup: Zod tem inferência de tipos TS mais forte, alinhada ao TS strict.
  VeeValidate pode ser usado como integração de formulário sobre Zod se a Phase 2 mostrar ganho.

## Consequences

### Positivas

- Separação clara server/client state; menos bugs de dados desatualizados.
- Tipagem ponta a ponta a partir do OpenAPI.

### Negativas / custos aceitos

- Curva de aprendizado de TanStack Query (query keys, invalidação).
- Geração de tipos adiciona uma etapa ao fluxo (tarefa Moon dedicada).

### Quando revisitar

Se a aplicação precisar de SSR/SEO (não previsto para um painel autenticado).
