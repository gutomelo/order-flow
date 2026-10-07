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

### Decisões de implementação (Phase 5)

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| Página de **detalhe** (`/customers/:id`) com seções de endereços e contatos | cliente B2B é um agregado: dados cadastrais + N endereços + N contatos não cabem num diálogo | um diálogo gigante com abas; listas separadas por recurso |
| Papéis (cobrança, entrega padrão, principal) movidos por **ação** (`set-billing`...), não por checkbox no formulário | a regra "exatamente um" é do backend (AD3/CT2); o frontend só pede "torne este" e recarrega | marcar/desmarcar no formulário e deixar o usuário criar estados inválidos |
| `useZodForm` **foca o primeiro campo inválido** (validação local e erro de campo do servidor) | regra de UI do projeto que nenhum formulário cumpria desde a Phase 2 | foco manual em cada formulário |
| Após mover papel ou remover, o foco vai para o cartão afetado ou para o título da seção (`tabindex="-1"`) | o botão clicado deixa de existir e o foco caía no `<body>` — quem usa teclado perdia a posição | deixar o navegador decidir |
| `FormAlert` (erro geral de formulário) extraído para `components/ui` e aplicado aos 11 formulários existentes | o mesmo bloco estava copiado em 10 arquivos, com dois estilos diferentes | manter a cópia |
| Token `--color-link` | `primary` como **texto** sobre a superfície escura tem contraste 3,45:1 (falha AA); o Lighthouse apontou no e-mail do contato | escurecer o `primary` (mudaria botões) |
| Ações com texto visível + contexto (`Tornar cobrança` + `: Filial Campinas`) usam texto visível `aria-hidden` e rótulo completo em `sr-only` | o espaço em branco do template gerava "Tornar cobrança : Filial" e o nome acessível precisa conter o texto visível (WCAG 2.5.3) | `aria-label` montado por concatenação |
| Preenchimento por CEP (ViaCEP) **não** implementado | seria a primeira integração externa síncrona do cadastro; registrado em `customers.md` | — |

### Decisões de implementação (Phase 6)

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| Frontend **não soma dinheiro**: preços e totais vêm de `POST /orders/quote`, calculado pelo mesmo código do pedido | duas implementações de arredondamento divergem; o total mostrado precisa ser o total gravado | somar no cliente com `number` (float) |
| Envio confirma o total visto (`expected_total`); `PRICES_CHANGED` mostra o novo total e pede confirmação | tabela alterada entre a prévia e o envio | aceitar o preço novo em silêncio |
| Detalhe de rascunho mostra a **cotação atual**, não a estimativa salva | o E2E mostrou tabela com R$ 2,90 e alerta com o novo total ao mesmo tempo | recotar só no envio |
| `useIdempotencyKey`: chave por conteúdo | retry após timeout precisa reaproveitar a chave; outro conteúdo é outra intenção | chave nova por clique (duplica pedido após timeout) |
| `SearchCombobox` genérico (Reka UI) usado por `ProductPicker` e `CustomerPicker` | segundo seletor com busca no servidor duplicaria o combobox | copiar o componente |
| Valores monetários como string decimal; `formatMoney`/`parseMoneyInput` em `utils/money.ts` ("3,50" → "3.50") | `float` e vírgula decimal pt-BR | `Number()` no input |
| `key` de diálogo **não** depende de dados recarregados | a recarga após criar uma tabela de preço remontava o diálogo aberto (bug achado no E2E; teste de regressão) | — |

### Decisões de implementação (Phase 7)

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| Coluna "Disponível" no editor e no pedido Pendente, com aviso em texto + ícone ("Acima do disponível", "Faltam N") | antecipar a falta sem bloquear (o backend decide na reserva) | bloquear o envio no cliente |
| Envio sem estoque → toast `warning` (novo tom), não erro | o pedido foi aceito (Pendente); não é falha nem sucesso pleno | toast de erro ou sucesso |
| Painel "Sem reserva de estoque" com "Reservar estoque" e a lista de faltas do `409` | pedido Pendente precisa de um próximo passo claro | só o status no selo |
| Mutations de pedido invalidam também `inventory` | reservar/cancelar muda o disponível mostrado em outras telas | invalidar só `orders` |

### Decisões de implementação (Phase 8)

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| Painel "Pagamento" no pedido com **cartão de teste** (select dos tokens do gateway simulado) e baixa manual com referência | sem gateway real, o cenário precisa ser escolhível; em produção o token viria do widget do provedor | campos de cartão no OrderFlow (PCI) |
| Idempotency-Key do pagamento muda após **qualquer resposta** do servidor; só falha de rede reaproveita | recusa gravada (ADR-012) faria "tentar com outro cartão" devolver a recusa antiga | chave só por conteúdo |
| `202` → toast `warning` "em processamento"; `409/422` → alerta no formulário | cobrança sem resposta não é sucesso nem erro | tratar 202 como sucesso |
| Polling (5 s) do pedido enquanto `awaitsBackgroundWork` | reconciliação e outbox concluem em background; o E2E mostrou a tela parada em "Aguardando pagamento" com o pagamento já aprovado (o polling parava antes do evento chegar ao pedido) | botão "atualizar" |
| Estorno manual pendente **não** faz polling | espera uma pessoa (financeiro), não o backend | polling indefinido |
| Códigos do provedor (`insufficient_funds`) traduzidos por i18n, com fallback para o código | código cru na tela; código novo não pode quebrar | mapear no backend |
| Página **Pagamentos** (`payments:read`) com "Tentar estorno de novo" (cartão `FAILED`) e "Confirmar estorno feito" (manual pendente), ambos com confirmação | o financeiro precisa de uma fila do que está travado | ações no detalhe do pedido |
| Cancelar pedido pago oferecido só com `orders:cancel_paid`, com texto sobre o estorno | espelha a política do backend (`permission_to_cancel`) | mesmo botão para todos |

### Decisões de implementação (Phase 9)

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| Tela **Expedição** (`/fulfillment`, `orders:process`) com uma aba por etapa, mais antigos primeiro (`ordering=submitted_at`) e o próximo passo na linha | o depósito trabalha por fila, não pedido a pedido | filtro de status na lista de pedidos |
| `FulfillmentActionButton` único (fila e detalhe) decide o próximo passo pelo status (`NEXT_FULFILLMENT_ACTION`) e pela permissão | duas telas com a mesma regra divergiriam | botões soltos por página |
| Separação em um clique; **despachar** e **confirmar entrega** com diálogo | o despacho baixa estoque e não pode ser desfeito; a entrega manual pede observação | confirmar tudo (atrito) ou nada (risco) |
| Erro do despacho (`503`) **dentro** do diálogo | com o `<dialog>` modal, o toast fica atrás do backdrop | toast |
| Botões da fila com o número do pedido para leitores de tela (`sr-only`) | a fila tinha vários "Iniciar separação" com o mesmo nome acessível (achado no E2E) | `aria-label` (substitui o texto visível) |
| Status `SHIPPED` exibido como **Despachado** | "Enviado" já significa o envio do pedido (`submitted_at`); o histórico mostrava "Pronto para envio → Enviado" num pedido "Enviado em…" (achado no E2E) | manter "Enviado" |
| Pedido em trânsito **sem** polling | a entrega leva dias; o TanStack Query recarrega ao voltar o foco para a aba | polling de horas |

### Decisões de implementação (Phase 10)

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| Criar usuário por **convite** é o padrão; senha inicial é opção | quem cria não deveria conhecer a senha de outra pessoa | só senha inicial |
| Erro de um campo escondido (senha, no modo convite) vai para o alerta do formulário | o E2E mostrou o envio "não fazendo nada": o `400` caiu num campo que não estava na tela | confiar no mapeamento genérico de campos |
| Tela "Definir senha" lê `uid`/`token` do fragmento e faz `router.replace` sem ele | token fora da barra de endereço e do histórico | query string |
| "Esqueci minha senha" mostra a mesma mensagem exista ou não a conta | não revelar quais e-mails existem | mensagem de "e-mail não encontrado" |
| Seção **Avisos ao cliente** no pedido, com e-mail mascarado; polling enquanto há envio pendente ou o pedido mudou há menos de 1 min | o aviso nasce pelo outbox segundos depois da mudança | polling contínuo |
| Selo **Convite pendente** e "Reenviar convite" na lista de usuários | o admin precisa saber quem ainda não entrou | — |

### Dashboard (Phase 11)

Responde "o que está acontecendo no negócio?" (`docs/domain/dashboard.md`). Decisões:

| Decisão | Problema | Alternativa descartada |
| --- | --- | --- |
| Filtro de período (Hoje / 7 / 30 dias) numa linha acima de tudo, na URL | os números da página precisam concordar entre si | filtro por gráfico |
| `BarChart` próprio em SVG: série única (sem legenda; o título nomeia), barras ≤ 24px com 4px arredondados na ponta, grade de 1px, tooltip no mouse **e** no teclado (setas), região `aria-live`, tabela equivalente em "Ver dados em tabela" | biblioteca de gráficos (~60–300 KB) para duas barras; acessibilidade por conta própria de qualquer jeito | Chart.js / ECharts |
| Cores do gráfico em tokens (`--color-chart-bar`, `--color-chart-grid`) com variante escura, validadas (contraste ≥ 3:1 na superfície clara e escura) | gráfico com hexadecimal solto e sem modo escuro | reaproveitar `--color-primary` sem validar |
| Variação: ícone colorido + texto em token de texto; cor diz se é bom (mais estorno = ruim); sem base = neutro | o verde de status tem 3,3:1 no branco — reprovado pelo Lighthouse **como texto** | texto colorido |
| Rótulos das barras lidos da string do backend (fuso do negócio), sem `Date` | converter para o fuso do navegador mudaria o dia | `toLocaleDateString` |
| Trocar o período mantém os números anteriores esmaecidos | sem pulo de layout nem esqueleto a cada clique | estado de loading |
| `min-w-0` nos itens da grade | no celular a tabela de recentes alargava a página (rolagem horizontal, achado no E2E) | — |
| Atualiza a cada 60 s e mostra "Atualizado às…" | mesmo TTL do cache do backend (ADR-014) | polling mais rápido |

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
