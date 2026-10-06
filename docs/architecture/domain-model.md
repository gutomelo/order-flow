# Modelo de domínio e fronteiras

## Context map

```mermaid
flowchart LR
    identity[identity]
    customers[customers]
    suppliers[suppliers]
    catalog[catalog]
    pricing[pricing]
    inventory[inventory]
    orders[orders]
    payments[payments]
    shipping[shipping]
    notifications[notifications]
    audit[audit]

    orders -->|valida cliente| customers
    orders -->|snapshot de produto| catalog
    orders -->|calcula preço| pricing
    orders -->|reserva/libera/consome| inventory
    orders -->|cobra/estorna| payments
    orders -->|cria remessa| shipping
    pricing --> catalog
    pricing --> customers
    inventory --> catalog
    catalog --> suppliers

    orders -. eventos .-> notifications
    orders -. eventos .-> audit
    inventory -. eventos .-> audit
    payments -. eventos .-> audit
    payments -. eventos .-> notifications
    shipping -. eventos .-> notifications
    payments -. payment.approved / payment.refunded .-> orders
```

Setas sólidas: chamada síncrona à camada `application` do módulo de destino.
Setas tracejadas: consumo de Domain Events.

**O grafo de dependências síncronas é acíclico.** `orders` é o coordenador do fluxo comercial;
módulos "abaixo" dele não o conhecem. Quando um módulo inferior precisa informar algo a `orders`
(ex.: refund concluído), ele publica um evento que `orders` consome.

`identity` é transversal: todos os módulos usam autenticação/autorização via `shared/permissions`,
mas nenhum módulo de negócio depende da lógica interna de `identity`.

## Donos dos dados

| Módulo | Dados (tabelas) | Expõe (application) |
| --- | --- | --- |
| `identity` | `Organization` (tenant), `User`, `Team`, blacklist de tokens | usuário atual, permissões efetivas, catálogo de permissões |
| `customers` | `CustomerSegment`, `Customer`, `CustomerAddress`, `CustomerContact` | `selectors.get_active_customer` |
| `suppliers` | `Supplier` | `selectors.get_active_supplier` |
| `catalog` | `Product`, `Category` | `selectors.get_sellable_products`, `selectors.descendant_ids` |
| `pricing` | `PriceList`, `PriceListItem` (descontos: fase futura) | `selectors.quote_prices(org, segment, products)` |
| `inventory` | `Warehouse`, `StockItem`, `StockReservation`, `StockMovement` | `ReserveStock`, `ReleaseReservation`, `ConfirmReservation`, `ConsumeReservation` |
| `orders` | `Order`, `OrderLine`, `OrderStatusHistory`, `OrderNumberSequence` (`OrderReturn`: Phase 9) | use cases do pedido |
| `payments` | `Payment`, `Refund` | `create_pending_card_payment`, `execute_charge`, `record_manual_payment`, `request_refund`, `retry_refund`, `confirm_manual_refund`; queries `payments_for_order`, `has_payment_in_flight` |
| `shipping` | `Shipment` | `CreateShipment` |
| `notifications` | `NotificationLog` | — (reage a eventos) |
| `audit` | `AuditLog` | `record(...)` usado por handlers |
| `shared` | `IdempotencyRecord`, `OutboxEvent`, `ProcessedEvent` (ADR-011) | infraestrutura |

Regra: **somente o dono escreve** nas suas tabelas. Leitura cross-módulo simples via ORM (para
joins/FKs) é tolerada; leitura com regra passa pela `application` do dono.

## Convenções de dados

| Tema | Convenção |
| --- | --- |
| Tenant | toda tabela de negócio tem `organization_id` (`shared.tenancy.TenantScopedModel`); unicidades de negócio são por organização (ADR-013) |
| IDs | UUID v4 como PK em entidades expostas na API; números legíveis (`Order.number`) separados |
| Dinheiro | `Decimal`; `NUMERIC(14,2)`; value object `Money` (valor + moeda `BRL`); arredondamento `ROUND_HALF_UP` em um único lugar |
| Moeda | campo `currency` (ISO 4217) nas entidades monetárias, fixo em `BRL` no MVP — expansão futura sem migração estrutural |
| Datas | `timestamptz`, UTC, `timezone.now()`; frontend converte para o fuso do usuário |
| Timestamps | `created_at`, `updated_at` (exceto tabelas append-only) |
| Quantidades | inteiros; unidades fracionadas fora do MVP |
| Enums | `TextChoices` com valores em inglês `SCREAMING_SNAKE_CASE` |

## Soft delete — decisão por entidade

| Entidade | Estratégia | Motivo |
| --- | --- | --- |
| `Customer` | inativação (`is_active=False`) | referenciado por pedidos históricos; não pode sumir |
| `Product` | inativação (`is_active=False`) | idem; pedidos guardam snapshot, mas FKs continuam |
| `Supplier`, `Warehouse`, `Category` | inativação | idem |
| `User` | inativação (`is_active` do Django) | auditoria referencia o usuário |
| `Order` | nunca removido; `CANCELLED` | histórico comercial |
| `StockMovement`, `AuditLog`, `OrderStatusHistory` | append-only, sem delete | rastreabilidade |
| `Payment`, `Refund` | nunca removidos | registro financeiro |
| `IdempotencyRecord` | remoção física após expirar | dado técnico temporário |

"Inativar" é explícito e auditado; não usamos um `deleted_at` genérico com manager que esconde
registros (fonte comum de bugs silenciosos).

## Auditoria

`AuditLog` registra operações relevantes: `ORDER_CREATED`, `ORDER_CANCELLED`,
`ORDER_STATUS_CHANGED`, `STOCK_ADJUSTED`, `PAYMENT_REFUNDED`, `USER_PERMISSION_CHANGED`, etc.
Campos: `actor_id`, `action`, `entity_type`, `entity_id`, `occurred_at`, `request_id`, `changes`
(JSONB com antes/depois relevantes, sem dados sensíveis), `reason`.

Operações críticas (ajuste de estoque, mudança de permissão, refund) são auditadas **na mesma
transação** (handler `in_transaction`); demais podem ser `after_commit`.

## Histórico do pedido

`OrderStatusHistory`: `order`, `from_status`, `to_status`, `changed_by` (nulo para sistema),
`changed_at`, `reason`. Gravado pelo use case na mesma transação da transição.
