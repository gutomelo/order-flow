# Frontend

Stack: Vue 3 · TypeScript strict · Vite · Vue Router · Pinia · TanStack Query for Vue · Axios ·
Zod · vue-i18n · Vitest · pnpm. Decisão: ADR-003.

## Estrutura

```text
frontend/src/
├── app/
│   ├── router/           # router, guards de autenticação/permissão
│   ├── layouts/          # AppLayout (sidebar + topbar), AuthLayout
│   ├── providers/        # QueryClient, i18n, pinia
│   ├── i18n/locales/     # pt-BR (chaves em inglês)
│   ├── pages/            # páginas transversais (NotFoundPage)
│   ├── stores/           # Pinia: client state (ui; session na Phase 2)
│   ├── navigation.ts     # itens da sidebar
│   └── styles/           # tokens.css, main.css
├── modules/              # features
│   ├── auth/  dashboard/  customers/  suppliers/  products/  inventory/
│   └── orders/  payments/  users/  settings/
├── components/           # design system: ui/ (Button, Input, Dialog…), data/ (DataTable, StatusBadge, EmptyState)
├── composables/          # composables genéricos (useConfirm, usePagination, useToast)
├── services/
│   └── http/             # cliente Axios, interceptors, normalização de erro
├── testing/              # helpers de teste (mountWithPlugins)
├── types/                # tipos globais e tipos gerados do OpenAPI (Phase 2)
└── utils/                # formatação de moeda/data, helpers puros
```

Feature (`src/modules/orders/`): `api/`, `components/`, `composables/`, `pages/`, `schemas/`,
`types/`, `tests/`, `routes.ts` — criando só o que for usado (template `.claude/templates/vue-feature.md`).

## Estado

| Tipo | Ferramenta | Exemplos |
| --- | --- | --- |
| Server state | TanStack Query | pedidos, clientes, produtos, estoque, dashboards |
| Client state | Pinia | sessão (access token em memória), usuário atual e permissões, preferências, sidebar recolhida, tema |
| Estado de URL | Vue Router (query params) | filtros, página, ordenação das tabelas |
| Estado local | `ref`/`reactive` no componente | formulário em edição, diálogo aberto |

Regras: query keys centralizadas por feature; mutations invalidam as keys afetadas; nunca copiar
resultado de query para o Pinia.

## Integração HTTP

- Um cliente Axios (`src/services/http`) com:
  - `Authorization: Bearer <access>` a partir do store de sessão;
  - refresh automático em 401 (uma única tentativa concorrente; refresh token vai no cookie HttpOnly);
  - `X-Request-ID` gerado por requisição (correlação com logs do backend);
  - `Idempotency-Key` em mutations marcadas como idempotentes;
  - normalização do envelope de erro em `ApiError { code, message, details, status }`.
- Tipos da API gerados do OpenAPI (tarefa Moon `frontend:generate-api-types`, Phase 2).
- Dinheiro trafega como string decimal; formatação com `Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })`.
  Cálculos monetários **não** são feitos no frontend (exceto prévias visuais claramente rotuladas).
- Datas trafegam em UTC; exibição no fuso do navegador do usuário via `Intl.DateTimeFormat`.

## Formulários

Zod para schema e mensagens (via i18n); validação client-side é feedback antecipado — o backend é a
autoridade e seus erros (`VALIDATION_ERROR.details.fields`) são mapeados para os campos.
Cada formulário: labels, help text quando necessário, erro inline, loading no submit, botão
desabilitado durante envio (anti double-submit), foco no primeiro erro.

## Design system

### Identidade

Profissional, precisa, estável, confiável. Referências de hierarquia e densidade: Linear, Stripe
Dashboard, GitHub, Shopify Admin, Vercel (sem copiar). Evitar gradientes exagerados, glassmorphism,
sombras pesadas e animações sem função.

### Tokens

Nenhum hexadecimal em componentes. Paleta base → tokens semânticos em `src/app/styles/tokens.css`:

| Token semântico | Light | Uso |
| --- | --- | --- |
| `--color-primary` | `#2563EB` | ações primárias, links, foco |
| `--color-primary-hover` | `#1D4ED8` | hover de ação primária |
| `--color-primary-subtle` | `#DBEAFE` | fundos de seleção, badges info leves |
| `--color-background` | `#F8FAFC` | fundo da aplicação |
| `--color-surface` | `#FFFFFF` | cards, tabelas, diálogos |
| `--color-sidebar` | `#0F172A` | sidebar |
| `--color-text-primary` | `#0F172A` | texto principal |
| `--color-text-secondary` | `#64748B` | texto auxiliar, labels secundários |
| `--color-border` | `#E2E8F0` | bordas e divisores |
| `--color-success` | `#16A34A` | sucesso, entregue |
| `--color-warning` | `#D97706` | atenção, aguardando |
| `--color-danger` | `#DC2626` | erro, cancelado, ações destrutivas |
| `--color-info` | `#0284C7` | informação |

Dark mode: os mesmos tokens redefinidos sob `[data-theme="dark"]` (e `prefers-color-scheme` como
padrão). Componentes nunca mudam por tema — só os tokens. Também há tokens de espaçamento
(escala 4px), raio, tipografia e elevação (sombras sutis).

Validar contraste AA de cada par texto/fundo ao definir os valores de dark mode (ex.: `--color-text-secondary` sobre `--color-surface`).

### Tipografia

```css
font-family: Inter, ui-sans-serif, system-ui, sans-serif;
```

Escala contida (12/14/16/20/24/30), números tabulares (`font-variant-numeric: tabular-nums`) em
tabelas e valores monetários.

### Layout

```text
┌────────────────────────────────────────────┐
│ Topbar (busca, usuário, tema)              │
├────────────┬───────────────────────────────┤
│ Sidebar    │ Page Header (título, ações)   │
│ Dashboard  │                               │
│ Orders     │ Content                       │
│ Inventory  │                               │
│ Products   │                               │
│ Customers  │                               │
│ Suppliers  │                               │
│ Reports    │                               │
│ Settings   │                               │
└────────────┴───────────────────────────────┘
```

Sidebar recolhível (ícone + texto; só ícone com tooltip quando recolhida), rota ativa destacada
(cor + indicador lateral + `aria-current="page"`). No mobile vira drawer. Itens visíveis conforme
permissões do usuário (UX; o backend continua autorizando).

### Componentes-chave

- **DataTable**: paginação, busca, filtros, ordenação, seleção, ações por linha e em lote,
  skeleton, empty state, error state com "tentar novamente", scroll horizontal no mobile.
- **StatusBadge**: mapa único status → ícone + rótulo i18n + token de cor. Ex.: `PAID` → ícone de
  cartão + "Pago" + info; `DELIVERED` → check + "Entregue" + success; `CANCELLED` → x + "Cancelado"
  + danger. Nunca só cor.
- **EmptyState**: título, explicação e ação ("Nenhum pedido encontrado. Crie o primeiro pedido ou
  ajuste os filtros utilizados." + botão).
- **ConfirmDialog**: para ações destrutivas, com texto específico ("Cancelar pedido OF-2026-000123?")
  e botão com o verbo da ação.
- **Toast**: feedback de sucesso/erro de mutations.

### Decisões de implementação (Phase 1)

| Tema | Decisão | Por quê |
| --- | --- | --- |
| Estilo | **Tailwind CSS v4** com `--color-*: initial` em `src/app/styles/tokens.css` | a paleta padrão é removida: só existem utilitários gerados dos tokens semânticos (`bg-surface`, `text-text-secondary`), então cores fora do design system nem compilam — a regra "sem hex em componentes" é garantida pela ferramenta |
| Dark mode | mesmos tokens redefinidos em `[data-theme="dark"]` e em `prefers-color-scheme` | componentes não conhecem o tema; preferência (claro/escuro/sistema) no store `ui` |
| Primitivas headless | **adiadas para a Phase 2** (avaliar Reka UI) | ainda não há diálogos/menus complexos; o drawer mobile usa `<dialog>` nativo (focus trap, Esc, `inert`) |
| Ícones | `@lucide/vue` | SVGs tree-shakeable, sempre com `aria-hidden` + texto |
| Fonte | Inter self-hosted (`@fontsource-variable/inter`) | sem CDN externo (privacidade, CSP) |
| TypeScript | ~6.0 (versão usada pelo `create-vue` oficial) | TS 7 ainda não é suportado pelo `vue-tsc` |

Validação: Lighthouse (desktop) Accessibility 100 e Best Practices 100 no dashboard.

### Decisões de implementação (Phase 2)

| Tema | Decisão | Por quê |
| --- | --- | --- |
| Sessão | access token só em memória (store `session`); refresh por cookie HttpOnly; `restore()` no primeiro guard de rota | XSS não consegue ler credenciais; recarregar a página não desloga |
| Refresh concorrente | uma única promessa de refresh compartilhada (*single-flight*) | refreshes paralelos usariam um cookie já rotacionado e derrubariam a sessão |
| Cliente HTTP × sessão | o store registra hooks no cliente (`configureAuth`) | sem import circular; cliente testável com adapter em memória |
| Rotas | `meta.public` e `meta.permission`; sem sessão → `/login?redirect=`; sem permissão → `/forbidden` | UX coerente com o RBAC (o backend continua sendo a autoridade) |
| Redirect pós-login | só caminhos internos (`/…`, nunca `//…`) | evita *open redirect* |
| Formulários | `useZodForm`: schema Zod com mensagens como chaves i18n; erros `VALIDATION_ERROR` do backend mapeados para os campos; envio bloqueado enquanto em andamento | uma regra de formulário para todas as features, sem dependência extra |
| Diálogos e menus | `<dialog>` nativo (`BaseDialog`, `ConfirmDialog`), `<select>` nativo e padrão *disclosure* no menu do usuário | acessíveis sem biblioteca; primitivas headless (Reka UI) só quando surgir combobox com busca (Phase 6) |
| Feedback | `ToastRegion` com `aria-live` | anuncia sucesso/erro sem mover o foco |

### Decisões de implementação (Phase 3)

Com três listagens (usuários, produtos, fornecedores) o padrão se repetiu e foi extraído:

| Peça | O que resolve |
| --- | --- |
| `DataTable` (genérico, slots `cell-<key>`) | estados obrigatórios (skeleton, erro com retry, vazio × sem resultado de filtro), paginação, `caption`, scroll horizontal |
| `useUrlFilters` | filtros e página na query string, com parsers por campo; `page` volta a 1 quando um filtro muda |
| `SearchInput` | busca com debounce, sincronizada com a URL |
| `useActivationToggle` | ativar/inativar com confirmação; sucesso vira toast, **erro aparece dentro do diálogo** (ver Phase 4) |
| `useZodForm` | passou a mostrar no **próprio campo** erros de domínio com `details.field` (ex.: `INVALID_BARCODE`), não só erros de validação |

- Ações de gestão e colunas dependentes de outras permissões são ocultadas, e as consultas
  correspondentes **nem são feitas** (ex.: SALES lê o catálogo, mas não consulta fornecedores).
- Texto com estado anexado (`Sul Express (inativo)`) é renderizado como um único nó de texto:
  nós separados perdem o espaço para leitores de tela.

### Decisões de implementação (Phase 4)

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| `ProductPicker` com **Reka UI** `Combobox` (busca no servidor, debounce de 250 ms) | escolher 1 entre milhares de produtos; um `<select>` não escala e um combobox acessível (teclado, `aria-activedescendant`, anúncios) é caro de acertar à mão | combobox próprio; Headless UI (sem Vue 3 ativo); carregar todos os produtos num `<select>` |
| Combobox **sem portal** dentro de `<dialog>` | o `<dialog>` modal fica na *top layer* e deixa o resto da página inerte: uma lista "portada" para o `body` fica atrás do backdrop e não recebe clique | portal + `z-index` (não vence a top layer) |
| Erros **dentro** de diálogos modais (`ConfirmDialog` ganhou `error`) | pelo mesmo motivo, um toast disparado com o modal aberto fica invisível e não é anunciado — a inativação de depósito com saldo (409) falhava "em silêncio" em todas as telas com ativar/inativar | toast com `z-index` maior; fechar o diálogo antes de mostrar o erro (a pessoa perde o contexto) |
| Mutations de estoque invalidam `inventoryKeys.all` em `onSettled` (não só em `onSuccess`) | um 409 de conflito significa que **a tela está desatualizada**: precisa recarregar justamente no erro | invalidar só no sucesso |
| `mutationFn: (input) => api(input)` | o TanStack Query v5 passa um 2º argumento (contexto) à `mutationFn`; repassar a função da API direto enviaria esse objeto como parâmetro | — |
| Ajuste envia o saldo exibido como `expected_on_hand`; no `STOCK_CHANGED_SINCE_COUNT` o diálogo **recarrega o item**, mostra "mudou de X para Y" e recalcula a diferença | sem isso o diálogo guardava o saldo antigo e todo reenvio falhava; com recarga silenciosa, a contagem seria aplicada sobre um saldo que a pessoa não viu | sobrescrever sem checar (perde movimentações); pedir para fechar e reabrir |
| `SelectField` usa `aria-required` em vez de `required` | os formulários usam `novalidate`; o `required` nativo num `<select>` vazio é exposto como `invalid` antes de qualquer interação | — |
| Filtro de datas em movimentações converte o **dia local** para limites UTC (`localDayBoundsToUtc`) | "movimentações de 04/10" deve significar o dia no fuso da pessoa, não em UTC | mandar a data crua e deixar o backend supor o fuso |

### Dashboard

Responde "o que está acontecendo no negócio?": cards (pedidos de hoje, faturamento, pedidos
pendentes, produtos com estoque baixo), gráficos (vendas no período, pedidos por status) e tabela de
pedidos recentes. Nada de gráficos sem pergunta de negócio associada.

## Acessibilidade e responsividade

WCAG 2.2 AA: contraste, navegação por teclado, foco visível, HTML semântico, labels, ARIA apenas
quando necessário, mensagens de erro associadas, status com ícone + texto. Desktop-first, funcional
em tablet e mobile (drawer, tabelas com scroll ou layout em cards, ações principais acessíveis).

## Internacionalização

UI inicial em pt-BR via vue-i18n; chaves em inglês por feature (`orders.list.emptyTitle`).
Nenhuma string visível literal em componentes. Formatação de números, moeda e datas via `Intl`
com o locale ativo.

## Testes

Vitest + Vue Test Utils: composables (com `QueryClient` de teste), schemas Zod, utilitários de
formatação e componentes com lógica. E2E (Playwright) avaliado após a Phase 6 para o fluxo de pedido.
