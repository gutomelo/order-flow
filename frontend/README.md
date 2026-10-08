# Frontend — OrderFlow

SPA de operação B2B em **Vue 3** (`<script setup>`, Composition API) com **TypeScript 6 strict**, **Vite 8**, **TanStack Query** para estado do servidor e **Tailwind CSS v4** usado só com design tokens. Este documento explica a arquitetura do frontend, o design system e as decisões que o tornam mais que um conjunto de telas sobre uma API.

> Visão do produto e execução: [README da raiz](../README.md) · Backend: [backend/README.md](../backend/README.md) · Contexto para o agente de IA: [CLAUDE.md](../CLAUDE.md)

![Detalhe do pedido](../docs/images/order-detail.png)

## Sumário

- [Visão geral](#visão-geral)
- [Estrutura](#estrutura)
- [Arquitetura](#arquitetura)
- [Estado e dados](#estado-e-dados)
- [Design system](#design-system)
- [Acessibilidade](#acessibilidade)
- [Segurança](#segurança)
- [Regras de negócio no cliente](#regras-de-negócio-no-cliente)
- [Estratégia de testes](#estratégia-de-testes)
- [Diferenciais de engenharia](#diferenciais-de-engenharia)
- [Como rodar, testar e construir](#como-rodar-testar-e-construir)

## Visão geral

Uma aplicação atende todos os papéis da organização. O menu e as ações seguem as **permissões** do usuário (`orders:create`, `payments:refund`, `inventory:adjust`...): quem é do armazém vê a fila de expedição e o estoque, mas não o financeiro. Ela fala só com a API (`/api/v1`). Em desenvolvimento o Vite repassa `/api` e `/health` para o backend, sem CORS a configurar.

| Área          | Rotas                                                                                        | O que faz                                                                                                                                     |
| ------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Acesso        | `/login`, `/forgot-password`, `/reset-password`                                              | Login; redefinição de senha e aceite de convite pelo link do e-mail                                                                           |
| Gestão        | `/dashboard`, `/audit`                                                                       | Indicadores com comparação de período, gráfico de faturamento, funil, saúde do sistema; trilha de auditoria filtrável                         |
| Pedidos       | `/orders`, `/orders/new`, `/orders/:id/edit`, `/orders/:id`                                  | Lista com busca e filtro, editor de rascunho com preço por segmento, detalhe com reserva, pagamento, expedição, avisos ao cliente e histórico |
| Operação      | `/fulfillment`, `/payments`                                                                  | Fila de expedição (a separar, em separação, prontos, em trânsito); cobranças e estornos com confirmação de estorno manual                     |
| Estoque       | `/stock`, `/movements`, `/warehouses`                                                        | Saldo físico/reservado/disponível, recebimento, ajuste, transferência, ponto de reposição, ledger de movimentações                            |
| Cadastros     | `/products`, `/categories`, `/suppliers`, `/customers`, `/customer-segments`, `/price-lists` | Catálogo, fornecedores, clientes (endereços e contatos), segmentos e tabelas de preço                                                         |
| Administração | `/users`, `/teams`                                                                           | Usuários (convite por e-mail, papel, ativação) e equipes                                                                                      |

| Pedidos                                        | Expedição                                            | Celular                                                      |
| ---------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------ |
| ![Lista de pedidos](../docs/images/orders.png) | ![Fila de expedição](../docs/images/fulfillment.png) | ![Dashboard no celular](../docs/images/dashboard-mobile.png) |

## Estrutura

```text
frontend/src/
├── app/            bootstrap: router (guards), layouts (AppLayout, AuthLayout), navegação, i18n (pt-BR),
│                   providers (QueryClient), stores globais (UI, toasts), styles/tokens.css
├── modules/        uma pasta por feature: auth, dashboard, orders, payments, inventory, catalog,
│                   customers, suppliers, pricing, users, audit
├── components/ui/  design system: BaseButton, TextField, SelectField, SearchCombobox, DataTable,
│                   TablePagination, StatusBadge, BaseDialog, ConfirmDialog, EmptyState, FormAlert, ToastRegion...
├── composables/    useZodForm, useUrlFilters, useIdempotencyKey, useApiErrorMessage, useActivationToggle
├── services/http/  cliente Axios único e ApiError (envelope de erro normalizado)
├── testing/        mountWithPlugins e builders de dados
├── types/          tipos compartilhados (paginação, dinheiro)
└── utils/          formatação de dinheiro e datas no fuso do usuário
```

### Organização de uma feature

```text
modules/orders/
├── routes.ts                  # rotas lazy com meta { permission, titleKey }
├── api/ordersApi.ts           # data-access: funções tipadas sobre o cliente HTTP
├── composables/useOrders.ts   # query keys + useQuery/useMutation com invalidação explícita
├── types.ts                   # contratos da API (unions exatas de status)
├── pages/                     # containers: OrdersPage, OrderEditorPage, OrderDetailPage, FulfillmentPage
├── components/                # apresentação: OrderPaymentPanel, OrderFulfillmentPanel, OrderLinesEditor...
└── tests/                     # comportamento visível: página montada com o app inteiro
```

Cada feature segue o mesmo fluxo: **api → composables (Query) → pages → components**. Só existem as pastas que a feature usa: nada de `schemas/` vazio "por padrão".

## Arquitetura

- **Vue 3 moderno:** `<script setup lang="ts">`, props e emits tipados, `defineModel`, `useId`. Sem Options API.
- **Rotas lazy por feature** com `meta.permission`. Um guard global:
  - restaura a sessão pelo cookie de refresh na primeira navegação;
  - leva ao login guardando o destino;
  - manda para `/forbidden` quem não tem a permissão.

  O título da aba acompanha a rota ("Pedidos · OrderFlow").

- **Cliente HTTP único** (`services/http/client.ts`). Componentes nunca chamam o Axios.

| Responsabilidade               | Detalhe                                                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `X-Request-ID`                 | Gerado por requisição; liga a tela ao log do backend, ao worker e ao trace                                      |
| `Authorization: Bearer`        | A partir da sessão em memória                                                                                   |
| `X-Requested-With`             | Exigido pelos endpoints de sessão (defesa contra CSRF no cookie de refresh, ADR-007)                            |
| 401 → refresh → nova tentativa | Várias requisições com 401 ao mesmo tempo aguardam **o mesmo** refresh (single-flight)                          |
| `ApiError`                     | Todo erro normalizado do envelope `{"error": {"code", "message", "details"}}`; falha de rede tem `status: null` |

- **Layout:** `AppLayout` com landmarks (`header`, `nav`, `main`) e link "Pular para o conteúdo". A sidebar é recolhível (preferência lembrada) e vira gaveta no celular.

## Estado e dados

- **Server state → TanStack Query; client state → Pinia** ([ADR-003](../docs/adr/003-vue-typescript.md)). Pedidos, estoque, clientes e indicadores nunca são copiados para o Pinia. O Pinia guarda só a sessão, as preferências de UI e os toasts.
- **Query keys por feature** (`ordersKeys.list(filters)`, `ordersKeys.detail(id)`) e **invalidação explícita** em `onSettled` das mutations. O detalhe do pedido acompanha em segundo plano o trabalho assíncrono do backend (pagamento em reconciliação, rastreio) até o estado assentar.
- **Filtros na URL** (`useUrlFilters`): busca, status e página sobrevivem a recarregar e podem ser compartilhados por link.
- **Formulários com Zod** (`useZodForm`):
  - validação local só de formato;
  - erros do servidor (`details.fields`) viram erros de campo;
  - foco no primeiro campo inválido;
  - envio duplo bloqueado enquanto a mutation está pendente.
- **Erros por `code`:** `useApiErrorMessage` traduz pelo i18n os códigos gerados no cliente (`NETWORK_ERROR`...) e usa a `message` pt-BR que o backend já envia no envelope. Erro que pertence a um campo escondido vai para o alerta do formulário, para não sumir.

## Design system

Estética de SaaS B2B: densidade de informação, hierarquia clara, sem gradientes nem animações sem função. Especificação: [docs/architecture/frontend.md](../docs/architecture/frontend.md).

### Design tokens

`app/styles/tokens.css` define as cores semânticas como CSS custom properties, expostas ao Tailwind v4 (`bg-surface`, `text-text-secondary`, `border-border`...). **Nenhum hexadecimal em componente.**

| Categoria           | Tokens                                                                                                     |
| ------------------- | ---------------------------------------------------------------------------------------------------------- |
| Superfícies e texto | `surface`, `surface-muted`, `background`, `text-primary`, `text-secondary`, `border`                       |
| Marca e estados     | `primary`, `primary-hover`, `primary-subtle`, `on-primary`, `link`; `success`, `warning`, `danger`, `info` |
| Foco e gráficos     | `focus-ring`, `chart-bar`, `chart-grid`                                                                    |
| Navegação           | `sidebar`, `sidebar-hover`, `sidebar-text`, `sidebar-text-active` (sidebar escura nos dois temas)          |
| Tipografia          | Inter; `tabular-nums` em valores e quantidades                                                             |

**Tema claro, escuro e sistema:** segue `prefers-color-scheme` por padrão, com escolha explícita via `data-theme` no `<html>`. A preferência fica em `localStorage`, tolerando a falta dele (modo privado).

### Componentes (`components/ui`)

| Componente                                  | Destaque                                                                                                                          |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `DataTable` + `TablePagination`             | `<table>` semântica, skeleton no carregamento, estados vazio e de erro, rolagem horizontal no celular                             |
| `StatusBadge`                               | Status com **ícone + texto** (nunca só cor); usado por pedido, pagamento, estorno, remessa e aviso                                |
| `ConfirmDialog` / `BaseDialog`              | `<dialog>` nativo modal: focus trap, `Esc`, foco devolvido; texto específico ("Despachar o pedido #000039?")                      |
| `SearchCombobox`                            | Busca assíncrona acessível (Reka UI), usada para escolher cliente e produto                                                       |
| `TextField`, `SelectField`, `TextAreaField` | `<label>` associado, help text e erro ligados por `aria-describedby`                                                              |
| `EmptyState`, `FormAlert`, `ToastRegion`    | Vazio explica o porquê e o próximo passo; toasts em região `aria-live`                                                            |
| Gráficos do dashboard                       | `BarChart` e `PipelineBars` em **SVG próprio**, navegáveis por teclado, com a tabela de dados equivalente ("Ver dados em tabela") |

Biblioteca de componentes completa não foi necessária: o Reka UI entra só no combobox, onde poupa trabalho real de acessibilidade.

## Acessibilidade

Meta: **WCAG 2.2 AA**, verificada a cada fase com Lighthouse (acessibilidade 100 nas telas entregues) e navegação real no navegador.

- Navegação completa por teclado, `:focus-visible` visível, link "Pular para o conteúdo".
- **Gestão de foco:** foco no conteúdo principal a cada troca de rota; diálogos devolvem o foco; formulários focam o primeiro campo inválido.
- Botões repetidos em tabela têm nome acessível completo ("Iniciar separação do pedido #000018", "Ajustar SKU em CD-SP").
- Contraste conferido nos dois temas: a cor de status fica no ícone, não no texto. Isso veio de uma reprovação real no Lighthouse.
- Textos 100% via i18n em pt-BR; datas e dinheiro formatados no fuso e no padrão do usuário (`Intl`).

## Segurança

| Medida                           | Detalhe                                                                                                                                                                                  |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Access token **só em memória**   | Nunca em `localStorage` (um XSS o leria). Ao recarregar, a sessão volta pelo refresh token em cookie HttpOnly, com rotação no backend ([ADR-007](../docs/adr/007-jwt-authentication.md)) |
| Token fora da URL                | O link de convite/redefinição tem o token removido da barra de endereço assim que lido                                                                                                   |
| Sem open redirect                | `?redirect=` do login aceita só caminho interno                                                                                                                                          |
| Sem XSS por construção           | Nenhum `v-html`; dados da API só por interpolação                                                                                                                                        |
| Guards são UX                    | A autorização real é do backend; `403` vira mensagem na tela, sem perder o formulário                                                                                                    |
| Cabeçalhos na imagem de produção | nginx com `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`; assets com hash e cache imutável                                                                         |

## Regras de negócio no cliente

**O frontend não decide regra de negócio.** Ele valida formato para dar feedback rápido e exibe o que a API devolve:

- **Dinheiro trafega como string decimal** e é só formatado (`Intl.NumberFormat('pt-BR', { currency: 'BRL' })`). Totais, preços por segmento e faturamento vêm do backend; nenhuma soma de dinheiro em `number`.
- **Idempotência por intenção** (`useIdempotencyKey`, [ADR-012](../docs/adr/012-idempotency-keys.md)). Enquanto o conteúdo não muda e o resultado é incerto (falha de rede), reenviar reaproveita a mesma chave, e o backend devolve a resposta original em vez de criar outro pedido ou cobrar de novo. Resposta definitiva (aprovado, recusado) ou conteúdo diferente geram chave nova.
- **Estados assíncronos honestos:** "pagamento em processamento" (gateway sem resposta) é um estado próprio, nunca "falhou"; a tela acompanha até a reconciliação decidir.
- **Ações seguem estado e permissão vindos da API.** O botão só aparece quando a transição é possível, mas quem decide é a máquina de estados do backend.

## Estratégia de testes

**187 testes** em 34 arquivos (Vitest + Vue Test Utils, ambiente jsdom).

| Nível             | Cobre                                                                                                                                                                             |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Páginas (maioria) | O `App` inteiro montado numa rota (`mountWithPlugins`), com a camada `api/` da feature mockada. Verifica texto, foco, URL, chamadas à API e estados de carregamento, vazio e erro |
| Fluxos críticos   | Pagamento (chave mantida na falha de rede, trocada após resposta), expedição com confirmação, cancelamento com estorno, editor de rascunho, convite e redefinição de senha        |
| Infraestrutura    | Cliente HTTP (refresh single-flight, normalização de erro, `X-Request-ID`), guards de rota, sessão, composables, formatação de dinheiro e datas                                   |

Testes de comportamento visível, não de implementação. Cada fase também passou por **mutação manual**: retirar a invalidação, o foco no campo inválido, a troca de chave após recusa ou a permissão de uma ação tem que derrubar um teste. Houve ainda E2E no navegador real contra o backend completo, que achou bugs que os testes não pegavam:

- rolagem horizontal no celular;
- erro sumindo num campo escondido;
- contraste reprovado.

Estratégia: [testing-strategy](../docs/development/testing-strategy.md).

## Diferenciais de engenharia

1. **Separação estrita de estado.** Servidor no TanStack Query, cliente no Pinia, filtros na URL: nenhuma fonte de verdade duplicada.
2. **Correção respeitada no cliente.** Nenhuma regra de negócio na tela, dinheiro como string decimal e idempotência por intenção, testada no caso de falha de rede.
3. **Sessão segura por desenho.** Access token em memória, refresh HttpOnly com rotação, refresh single-flight, sem open redirect e sem token na URL.
4. **Acessibilidade como critério de aceite.** WCAG 2.2 AA, Lighthouse 100, gráficos em SVG navegáveis por teclado e com tabela equivalente, foco gerenciado.
5. **Design system por tokens.** Uma fonte de verdade de cor nos dois temas, componentes base pequenos e uma dependência de UI só onde ela paga o custo.
6. **TypeScript strict de ponta a ponta.** Sem `any`, contratos com unions exatas e `vue-tsc --build` no pipeline.
7. **Engenharia assistida por IA com Context Engineering.** Desenvolvido com Claude Code sobre contexto versionado (rules de frontend e de UI/acessibilidade, skill `create-vue-feature`) e revisão pelo subagent `ux-reviewer` ([detalhes](../README.md#context-engineering-e-desenvolvimento-assistido-por-ia)).

## Como rodar, testar e construir

Pelo Docker Compose da raiz o Vite sobe em <http://localhost:5173>, com recarga automática. Sem Docker (Node ≥ 24 e pnpm; o moon os provisiona):

```bash
pnpm install
pnpm dev                    # http://localhost:5173 (proxy /api e /health → VITE_API_PROXY_TARGET, padrão :8000)
pnpm test                   # 187 testes (Vitest)
pnpm test:watch
pnpm type-check             # vue-tsc --build
pnpm lint && pnpm format:check
pnpm build                  # build de produção (dist/), servido por nginx na imagem de produção
```

Pela raiz do monorepo:

```bash
moon run frontend:check     # lint + format-check + typecheck + test
moon run frontend:build
```

Para criar uma feature nova com a estrutura e as convenções corretas, use a skill `/create-vue-feature` ([.claude/skills](../.claude/skills)).
