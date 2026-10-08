---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.vue"
  - "frontend/package.json"
---

# Frontend Vue / TypeScript

- Vue 3 + `<script setup lang="ts">` + Composition API. Sem Options API.
- TypeScript `strict`. Proibido `any` (use `unknown` + narrowing). `vue-tsc` deve passar.
- Organização por feature em `src/modules/<feature>/` (`api/`, `components/`, `composables/`,
  `pages/`, `schemas/`, `types/`, `tests/`) — crie só as pastas que a feature usa.
- **Server state → TanStack Query** (orders, customers, products, inventory, dashboards).
  **Client state → Pinia** (sessão, usuário atual, preferências, UI global). Nunca duplicar dados
  remotos no Pinia.
- Query keys centralizadas por feature (`ordersKeys.list(filters)`), invalidação explícita após
  mutations.
- HTTP só via cliente Axios em `src/services/http` (interceptors de auth, `Idempotency-Key`,
  normalização do envelope de erro). Componentes não chamam Axios diretamente.
- Tipos da API derivados do schema OpenAPI do backend quando disponível; validação de formulários
  com Zod (`schemas/`).
- Regras de negócio são do backend; o frontend só antecipa feedback.
- Todo texto visível via i18n (`pt-BR`). Datas formatadas no fuso do usuário; dinheiro via
  `Intl.NumberFormat('pt-BR', { style: 'currency', currency })`, valores trafegam como string decimal.
- Componentes: props tipadas, emits tipados, sem lógica de dados em componentes de apresentação.
