# Eventos e processamento assíncrono

## Por quê

1. **Desacoplar efeitos secundários**: `PlaceOrder` não deve conhecer e-mail, analytics ou geração
   de documentos. Ele publica `OrderCreated`; quem se interessa reage.
2. **Não bloquear a requisição**: operações lentas ou dependentes de integrações rodam no Celery.
3. **Rastreabilidade**: eventos alimentam auditoria e notificações de forma uniforme.

## Infraestrutura (`shared/events`)

Explícita e sem framework de mensageria próprio. Implementada na Phase 8 com **Transactional
Outbox** (ADR-011):

```python
publish(event)                          # no use case, DENTRO da transação: grava em events_outbox
@subscribe("payments.payment.approved") # registra handler (importado no ready() do app consumidor)
def on_payment_approved(event: EventEnvelope) -> None: ...
```

| Peça | Execução |
| --- | --- |
| `publish` | grava `OutboxEvent` na transação do use case; fora de transação é erro |
| `events.relay_outbox` (Beat, 5 s) | `SKIP LOCKED` nos não publicados; enfileira uma task por (evento, handler) |
| `events.deliver` | cria `ProcessedEvent (evento, handler)` e roda o handler na mesma transação; retry exponencial |
| `maintenance.purge_published_events` | apaga publicados com mais de 30 dias |

Garantias:
- Rollback ⇒ o evento nunca existiu (nenhum evento "fantasma").
- Commit ⇒ o evento será entregue, mesmo que o processo caia ou o RabbitMQ esteja fora do ar.
- Entrega at-least-once, **efeito exactly-once por handler** (`ProcessedEvent` UNIQUE).
- Falha em handler não desfaz o caso de uso (consistência eventual) e não bloqueia os outros
  handlers do mesmo evento.

Não há modo síncrono `in_transaction`: a auditoria (Phase 12), que era o caso previsto para ele,
usa o outbox — o evento já é atômico com a mudança, o registro chega segundos depois e nenhum
módulo depende de `audit` (`docs/domain/audit.md`). Todo evento leva o `request_id`, o `correlation_id`
e o contexto do trace (`traceparent`) da origem: a entrega religa os ids nos logs e continua o
trace (ADR-015).

```mermaid
sequenceDiagram
    participant UC as CancelOrder
    participant DB as PostgreSQL
    participant Beat as Celery Beat (relay)
    participant W as Celery worker
    participant GW as PaymentGateway
    UC->>DB: BEGIN; pedido CANCELLED; libera estoque; Refund PENDING
    UC->>DB: INSERT events_outbox (payments.refund.requested)
    UC->>DB: COMMIT
    Beat->>DB: SELECT … FOR UPDATE SKIP LOCKED (não publicados)
    Beat->>W: events.deliver(evento, handler)
    W->>DB: INSERT ProcessedEvent (dedup)
    W->>GW: refund (fora de lock)
    W->>DB: Refund SUCCEEDED + outbox (payments.payment.refunded)
    Beat->>W: events.deliver → orders: CANCELLED → REFUNDED
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
| `orders.order.status_changed` ✅ | orders (`transition()`) | **notifications** (e-mails ao cliente); **audit** | outbox |
| `payments.payment.status_changed` ✅ | payments (toda mudança de status) | **audit** | outbox |
| `payments.refund.status_changed` ✅ | payments (toda mudança de status) | **audit** | outbox |
| `inventory.stock.changed` ✅ | inventory (`post_movement`, só recebimento/ajuste/transferência) | **audit** | outbox |
| `inventory.reorder_point.changed` ✅ | inventory (`update_reorder_point`) | **audit** | outbox |
| `StockReserved` | inventory | audit | in_transaction |
| `StockReleased` | inventory | audit | in_transaction |
| `StockReservationExpired` | inventory | audit, notifications (vendedor) | in_transaction / after_commit |
| `StockAdjusted` | inventory | audit | in_transaction |
| `inventory.stock.low` ✅ | inventory (`post_movement`) | **notifications** (estoque baixo); dashboard | outbox |
| `StockReceived`, `StockTransferred`, `StockReturned`, `StockConsumed` | inventory | audit | in_transaction |
| `payments.payment.approved` ✅ | payments | **orders** (`AWAITING_PAYMENT → PAID`; estorno se o pedido não pode mais ser pago) | outbox |
| `payments.refund.requested` ✅ | payments | **payments** (executa o estorno no gateway, fora da transação de quem pediu) | outbox |
| `payments.payment.refunded` ✅ | payments | **orders** (`CANCELLED → REFUNDED`) | outbox |
| `PaymentFailed` | payments | notifications | outbox (Phase 10) |
| `shipping.shipment.delivered` ✅ | shipping | **orders** (`SHIPPED → DELIVERED`) | outbox |
| `identity.user.invited` ✅ | identity | **notifications** (convite) | outbox |
| `identity.password_reset.requested` ✅ | identity | **notifications** (redefinição de senha) | outbox |

✅ = implementado (Phases 8 a 12). Eventos de identidade **nunca** levam token ou link: o e-mail
gera o link na hora do envio. Os demais são o planejado; nomes seguem `module.entity.action`.

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

## Estado atual (Phase 12)

- `audit` consome cinco eventos (pedidos, pagamentos, estornos, estoque manual, ponto de
  reposição). Os eventos de reserva/liberação/venda continuam sem consumidor: o pedido já é
  auditado pelas próprias transições e o ledger guarda os movimentos.

### Phase 10

- `notifications` é o primeiro módulo que só consome eventos: sete eventos viram e-mail.
  Handlers criam o registro; o envio é uma task da fila `notifications` após o commit
  (`docs/domain/notifications.md`).
- Prova de fogo no E2E: com o disco do host cheio, o RabbitMQ bloqueou as publicações; os eventos
  ficaram no outbox e foram todos entregues (com os e-mails) assim que o broker voltou.

### Phase 9

- `shared/events` com outbox (ADR-011 **Accepted**). Três eventos de `payments` e um de `shipping`,
  consumidos por `orders` e pelo próprio `payments` (tabela acima).
- O despacho é **síncrono** (`orders` chama `inventory` e `shipping` na mesma transação): baixa de
  estoque, remessa e status mudam juntos. Só a entrega pelo rastreio chega por evento, porque
  nasce num job do `shipping` que não conhece pedidos.
- A confirmação manual de entrega não publica evento: `orders` já muda o pedido na mesma
  transação. `OrderShipped`/`OrderDelivered` entram quando houver consumidor (notificações,
  Phase 10).
- A reserva de estoque continua **síncrona** (`orders` chama `inventory.application`): precisa
  de resposta imediata (tem ou não tem estoque), então não é evento.
- Na UI, o atraso do relay (até 5 s) aparece como estado intermediário honesto: a tela do pedido
  e a de pagamentos fazem polling enquanto há trabalho em background.
