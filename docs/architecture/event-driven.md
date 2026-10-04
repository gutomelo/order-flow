# Eventos e processamento assíncrono

## Por quê

1. **Desacoplar efeitos secundários**: `PlaceOrder` não deve conhecer e-mail, analytics ou geração
   de documentos. Ele publica `OrderCreated`; quem se interessa reage.
2. **Não bloquear a requisição**: operações lentas ou dependentes de integrações rodam no Celery.
3. **Rastreabilidade**: eventos alimentam auditoria e notificações de forma uniforme.

## Infraestrutura (`shared/events`)

In-process, simples e explícita — sem framework de mensageria próprio:

```python
publish(event)                                   # chamado pelo use case, dentro da transação
@subscribe(OrderCreated, mode="after_commit")    # registra handler (no ready() do app consumidor)
```

| Modo | Execução | Uso |
| --- | --- | --- |
| `in_transaction` | síncrono, dentro da transação do use case | efeito que deve ser atômico com a mudança (auditoria crítica) |
| `after_commit` | via `transaction.on_commit`; o handler normalmente apenas enfileira uma task Celery | e-mail, notificações, analytics, documentos |

Garantias:
- Rollback ⇒ handlers `after_commit` não executam (nenhum evento "fantasma").
- Handlers são idempotentes (deduplicação por `event_id` quando há efeito externo).
- Falha em handler `after_commit` não desfaz o caso de uso (consistência eventual); falha em
  `in_transaction` desfaz (por isso esse modo é restrito).

```mermaid
sequenceDiagram
    participant UC as PlaceOrder
    participant DB as PostgreSQL
    participant Bus as shared.events
    participant Audit as audit handler
    participant MQ as RabbitMQ
    participant W as Celery worker
    UC->>DB: BEGIN; insert order; reserve stock
    UC->>Bus: publish(OrderCreated)
    Bus->>Audit: in_transaction → AuditLog
    UC->>DB: COMMIT
    Bus->>MQ: on_commit → enqueue send_order_confirmation
    MQ->>W: task
    W->>W: idempotência por event_id → envia e-mail
```

## Estrutura de um evento

```python
@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: UUID          # gerado
    occurred_at: datetime   # UTC
    correlation_id: str     # do request/task de origem
    event_name: ClassVar[str]   # "orders.order.created"
    version: ClassVar[int]      # versão do schema do payload
```

Payload: primitivos serializáveis (UUID e Decimal como string), mínimo necessário, sem dados
sensíveis. Consumidores que precisam de mais dados consultam o módulo dono pelo ID.

## Catálogo de eventos

| Evento | Produtor | Consumidores | Modo |
| --- | --- | --- | --- |
| `OrderCreated` | orders | audit, notifications, analytics | audit: in_transaction · demais: after_commit |
| `OrderStatusChanged` | orders | audit | in_transaction |
| `OrderPaid` | orders | notifications, audit | after_commit / in_transaction |
| `OrderCancelled` | orders | notifications, audit | after_commit / in_transaction |
| `OrderShipped` | orders | notifications | after_commit |
| `OrderDelivered` | orders | notifications | after_commit |
| `StockReserved` | inventory | audit | in_transaction |
| `StockReleased` | inventory | audit | in_transaction |
| `StockReservationExpired` | inventory | audit, notifications (vendedor) | in_transaction / after_commit |
| `StockAdjusted` | inventory | audit | in_transaction |
| `StockLevelLow` | inventory | notifications, dashboard (invalidação de cache) | after_commit |
| `StockReceived`, `StockTransferred`, `StockReturned`, `StockConsumed` | inventory | audit | in_transaction |
| `PaymentApproved` | payments | audit, notifications | in_transaction / after_commit |
| `PaymentFailed` | payments | notifications | after_commit |
| `PaymentRefunded` | payments | **orders** (`CANCELLED/DELIVERED → REFUNDED`), audit, notifications | after_commit (candidato ao Outbox) |

Novos eventos: skill `create-domain-event` e atualização desta tabela.

## Celery

| Fila | Conteúdo | Observação |
| --- | --- | --- |
| `default` | tarefas gerais curtas | |
| `notifications` | e-mails, notificações | pode atrasar sem impacto de negócio |
| `integrations` | gateway de pagamento, frete, reconciliação | isolada: lentidão externa não afeta as demais |
| `maintenance` | expiração de reservas, limpezas, reconciliação de estoque | Celery Beat |

### Políticas

| Situação | Política |
| --- | --- |
| Erro transitório (timeout, 5xx, conexão) | `autoretry_for`, `retry_backoff=True` (exponencial), `retry_jitter=True`, `max_retries` explícito |
| Erro permanente (4xx de validação, regra de negócio) | sem retry; log `error` + registro de falha para reprocessamento manual |
| Tarefa duplicada (reentrega, at-least-once) | idempotência: checar estado/registro antes de agir; chaves únicas no banco |
| Worker morre no meio | `acks_late=True` em tasks que alteram estado → reentrega (por isso a idempotência) |
| Execuções periódicas sobrepostas | `select_for_update(skip_locked=True)` + lotes |
| Reprocessamento | tasks recebem IDs; podem ser reenfileiradas manualmente com segurança |

## Consistência eventual

O que é **forte** (mesma transação): pedido + linhas + reserva + movimentos + histórico + auditoria
crítica + registro de idempotência.
O que é **eventual**: notificações, analytics, documentos, transição `CANCELLED → REFUNDED` após o
gateway confirmar o refund.

A UI comunica estados intermediários honestamente (ex.: "Reembolso solicitado" enquanto o pedido
está `CANCELLED` aguardando `PaymentRefunded`).

## Transactional Outbox

`on_commit` tem uma janela de perda (processo cai entre o commit e o enfileiramento). Para eventos
com consequência de negócio (ex.: `PaymentRefunded` → `orders`), o ADR-011 propõe o Outbox.
A API `publish()` é a mesma nos dois modos. Decisão final antes da Phase 8.
