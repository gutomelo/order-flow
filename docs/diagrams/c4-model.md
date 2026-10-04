# C4 Model

Diagramas em Mermaid (renderizam no GitHub). Níveis: Context → Container → Component.

## Nível 1 — System Context

```mermaid
flowchart TB
    sales([Vendedor / Comercial])
    wh([Operador de depósito])
    fin([Financeiro])
    admin([Administrador / Gestor])

    of[["<b>OrderFlow</b><br/>Gestão B2B de pedidos e estoque"]]

    pay[(Provedor de pagamento<br/><i>externo</i>)]
    ship[(Provedor de frete<br/><i>externo</i>)]
    mail[(Serviço de e-mail<br/><i>externo</i>)]

    sales -->|cria pedidos, consulta clientes e estoque| of
    wh -->|separa, envia, ajusta estoque| of
    fin -->|acompanha pagamentos, estornos| of
    admin -->|usuários, permissões, catálogo, relatórios| of

    of -->|cobranças e estornos| pay
    of -->|remessas e rastreio| ship
    of -->|notificações| mail
```

Integrações externas começam como adapters fake (`FakePaymentGateway`, `FakeShippingProvider`,
`ConsoleEmailProvider`).

## Nível 2 — Containers

```mermaid
flowchart TB
    user([Usuário B2B])

    subgraph orderflow[OrderFlow]
        spa["<b>Web App</b><br/>Vue 3 + TypeScript (Vite)<br/>SPA servida estaticamente"]
        api["<b>API</b><br/>Django + DRF<br/>Modular Monolith"]
        worker["<b>Worker</b><br/>Celery<br/>tarefas assíncronas"]
        beat["<b>Scheduler</b><br/>Celery Beat<br/>tarefas periódicas"]
        db[("<b>Database</b><br/>PostgreSQL<br/>fonte da verdade")]
        cache[("<b>Cache</b><br/>Redis<br/>cache · throttling")]
        mq[["<b>Broker</b><br/>RabbitMQ"]]
    end

    ext[(Provedores externos<br/>pagamento · frete · e-mail)]

    user -->|HTTPS| spa
    spa -->|JSON/REST · JWT| api
    api -->|SQL · locks| db
    api --> cache
    api -->|enfileira tasks após commit| mq
    beat -->|agenda| mq
    mq --> worker
    worker --> db
    worker -->|HTTPS| ext
    api -->|chamadas síncronas curtas, fora de transação| ext
```

| Container | Tecnologia | Responsabilidade |
| --- | --- | --- |
| Web App | Vue 3, TS, TanStack Query, Pinia | UI, server state, feedback antecipado |
| API | Django, DRF, SimpleJWT, drf-spectacular | regras de negócio, autorização, persistência, OpenAPI |
| Worker | Celery | notificações, integrações, reconciliações |
| Scheduler | Celery Beat | expiração de reservas, limpezas, reconciliação |
| Database | PostgreSQL | dados e invariantes |
| Cache | Redis | cache de leitura, throttling |
| Broker | RabbitMQ | filas de tarefas |

## Nível 3 — Componentes da API (fluxo de pedido)

```mermaid
flowchart TB
    subgraph api[API — Django]
        subgraph orders[orders]
            ov[OrderViewSet<br/><i>api</i>]
            po[PlaceOrder / CancelOrder / PayOrder<br/><i>application</i>]
            sm[OrderStateMachine · Order rules<br/><i>domain</i>]
            exp[ExpireUnpaidOrder<br/><i>task</i>]
        end
        subgraph inventory[inventory]
            rs[ReserveStock / ReleaseReservation<br/><i>application</i>]
            ip[Stock policies<br/><i>domain</i>]
        end
        subgraph pricing[pricing]
            ps[PricingStrategy<br/>Standard · Wholesale · Contract]
        end
        subgraph payments[payments]
            cp[ChargePayment / RequestRefund]
            gw[PaymentGateway port<br/>FakePaymentGateway adapter]
        end
        subgraph shared[shared]
            ev[events: publish/subscribe]
            idem[idempotency]
            perm[permissions: HasPermission]
            err[exceptions: envelope de erro]
        end
        subgraph consumers[consumidores de eventos]
            au[audit handlers]
            no[notifications handlers]
        end
    end

    ov --> perm
    ov --> idem
    ov --> po
    po --> sm
    po --> ps
    po --> rs
    rs --> ip
    po --> cp
    cp --> gw
    po --> ev
    exp --> rs
    ev --> au
    ev --> no
    ov -.erros.-> err
```

## Nível 3 — Componentes do Frontend

```mermaid
flowchart LR
    subgraph app[app/]
        router[Router + guards]
        layout[AppLayout<br/>Sidebar · Topbar]
        providers[QueryClient · i18n · Pinia]
    end
    subgraph modules[modules/orders]
        pages[OrderListPage · OrderDetailPage]
        comps[components]
        composables[useOrderList · useCancelOrder<br/>TanStack Query]
        api[ordersApi]
        schemas[Zod schemas]
    end
    subgraph shared[shared]
        ds[components/: DataTable · StatusBadge · EmptyState · ConfirmDialog]
        http[services/http: Axios + interceptors]
        session[Pinia: session store]
    end

    router --> pages
    pages --> composables
    pages --> comps
    comps --> ds
    composables --> api
    api --> http
    http --> session
    pages --> schemas
```
