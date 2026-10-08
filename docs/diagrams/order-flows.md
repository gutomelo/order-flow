# Fluxos do pedido

Regras completas em [../domain/orders.md](../domain/orders.md) e
[../domain/inventory.md](../domain/inventory.md).

## Criar pedido (`POST /api/v1/orders`)

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente (SPA)
    participant API as OrderViewSet
    participant ID as Idempotency
    participant UC as PlaceOrder
    participant PR as Pricing
    participant INV as Inventory.ReserveStock
    participant DB as PostgreSQL
    participant EV as shared.events

    C->>API: POST /orders (Idempotency-Key)
    API->>API: autentica · orders:create · valida formato
    API->>UC: execute(PlaceOrderCommand)
    UC->>DB: BEGIN
    UC->>ID: registrar chave (IN_PROGRESS)
    UC->>PR: price_lines(customer, lines)
    PR-->>UC: preços e descontos
    UC->>DB: INSERT order (PENDING) + lines + history
    UC->>INV: reserve(lines)
    INV->>DB: SELECT ... FOR UPDATE stock_item ORDER BY id
    DB-->>INV: on_hand, reserved
    alt available >= quantity (todas as linhas)
        INV->>DB: UPDATE reserved; INSERT reservation + movement
        INV-->>UC: reservas
        UC->>DB: order → AWAITING_PAYMENT + history
        UC->>EV: publish(OrderCreated, StockReserved)
        UC->>ID: gravar resposta (COMPLETED)
        UC->>DB: COMMIT
        EV-->>EV: on_commit → tasks (notificações)
        API-->>C: 201 Created
    else alguma linha sem estoque
        INV-->>UC: InsufficientStock
        UC->>DB: ROLLBACK (inclusive a chave)
        API-->>C: 409 INSUFFICIENT_STOCK
    end
```

## Concorrência na última unidade

```mermaid
sequenceDiagram
    participant A as Tx A (cliente A)
    participant DB as PostgreSQL (stock_item: on_hand=1, reserved=0)
    participant B as Tx B (cliente B)

    A->>DB: SELECT ... FOR UPDATE (lock obtido)
    B->>DB: SELECT ... FOR UPDATE (aguarda lock)
    A->>DB: available=1 ≥ 1 → reserved=1
    A->>DB: COMMIT (libera lock)
    DB-->>B: lock obtido; lê reserved=1 (valor atualizado)
    B->>B: available=0 < 1 → InsufficientStock
    B->>DB: ROLLBACK
```

## Pagamento (`POST /api/v1/orders/{id}/pay`)

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente (SPA)
    participant UC as PayOrder
    participant DB as PostgreSQL
    participant GW as PaymentGateway
    participant INV as Inventory

    C->>UC: pay (Idempotency-Key)
    UC->>DB: Tx1: lock order (AWAITING_PAYMENT) · Payment PENDING · COMMIT
    UC->>GW: charge(payment_id, amount)  — fora de transação
    alt aprovado
        UC->>DB: Tx2: lock order + payment
        alt pedido ainda AWAITING_PAYMENT
            UC->>INV: confirm reservation
            UC->>DB: order → PAID · Payment APPROVED · COMMIT
            UC-->>C: 200 (PAID)
        else reserva expirou no intervalo
            UC->>INV: tentar reservar novamente
            alt conseguiu
                UC->>DB: order → PAID · COMMIT
            else sem estoque
                UC->>DB: Payment APPROVED · refund solicitado · COMMIT
                UC-->>C: 409 INSUFFICIENT_STOCK (refund em andamento)
            end
        end
    else recusado
        UC->>DB: Tx2: Payment FAILED · COMMIT
        UC-->>C: 422 PAYMENT_DECLINED (pedido segue AWAITING_PAYMENT)
    else timeout / indisponível
        UC-->>C: 202 Accepted (Payment PENDING)
        Note over UC,GW: task de reconciliação consulta o gateway com backoff
    end
```

## Expiração de reserva (Celery Beat)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat (1 min)
    participant UC as ExpireUnpaidOrder
    participant DB as PostgreSQL
    participant INV as Inventory.ReleaseReservation

    Beat->>UC: run
    UC->>DB: SELECT orders AWAITING_PAYMENT AND payment_due_at < now FOR UPDATE SKIP LOCKED LIMIT n
    loop cada pedido
        UC->>INV: release(order, reason=EXPIRED)
        INV->>DB: lock stock_items (ordem por id) · reserved -= q · movement RELEASE · reservation EXPIRED
        UC->>DB: order → PENDING + history (reason=RESERVATION_EXPIRED)
        UC->>UC: publish(StockReservationExpired)
    end
```

## Cancelamento de pedido pago

```mermaid
sequenceDiagram
    actor U as Usuário (orders:cancel_paid)
    participant UC as CancelOrder
    participant INV as Inventory
    participant PAY as Payments
    participant GW as PaymentGateway

    U->>UC: POST /orders/{id}/cancel (reason)
    UC->>UC: Tx: lock order · state machine PAID → CANCELLED
    UC->>INV: release reservation (RELEASE)
    UC->>PAY: RequestRefund (Refund PENDING)
    UC-->>U: 200 (CANCELLED · reembolso solicitado)
    PAY->>GW: refund (task, retry com backoff)
    GW-->>PAY: refunded
    PAY->>UC: PaymentRefunded (evento)
    UC->>UC: CANCELLED → REFUNDED
```

## Máquina de estados

Ver diagrama `stateDiagram-v2` em [../domain/orders.md](../domain/orders.md#estados).
