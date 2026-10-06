# ADR-011: Transactional Outbox para eventos críticos

- **Status:** Accepted (Phase 8 — Payments)
- **Data:** 2026-10-04 (proposta) · 2026-10-06 (aceita)
- **Relacionados:** ADR-004, ADR-005, `docs/architecture/event-driven.md`

## Context

Na abordagem inicial, Domain Events com efeito assíncrono são enfileirados no Celery via
`transaction.on_commit`. Existe uma janela de falha:

```text
COMMIT (pedido salvo)  →  processo cai / RabbitMQ indisponível  →  task nunca enfileirada
```

O pedido existe, mas o evento foi perdido: e-mail não enviado (tolerável) ou — mais grave — um
consumidor de negócio não reage (ex.: refund não solicitado após cancelamento de pedido pago).
O problema inverso (publicar antes do commit) gera eventos de algo que sofreu rollback.

## Decision

Adotar o **Transactional Outbox** para eventos com consequência de negócio. O gatilho foi a
Phase 8: aprovação de pagamento → pedido `PAID`, cancelamento de pedido pago → estorno, estorno
concluído → pedido `REFUNDED`. Perder qualquer um deles deixa dinheiro e pedido divergentes.

Desenho proposto (o implementado, com os ajustes, está em *Implementação* abaixo):
1. Tabela `outbox_event` (`id` UUID, `event_name`, `version`, `payload` JSONB, `occurred_at`,
   `published_at` nullable, `attempts`, `last_error`), escrita **na mesma transação** da mudança de
   negócio via `shared.events.publish(...)`.
2. Relay periódico (Celery Beat, a cada poucos segundos) seleciona eventos não publicados com
   `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n`, enfileira as tasks/handlers e marca `published_at`.
3. Entrega **at-least-once**: consumidores deduplicam por `event_id` (já exigido pelas regras de
   tasks idempotentes).
4. Limpeza periódica de eventos publicados antigos.

A API `shared.events.publish()` é a mesma nos dois modos — trocar `on_commit` por outbox não muda o
código dos módulos.

## Implementação (Phase 8)

App `shared.events` (código transversal, sem regra de módulo):

| Peça | Onde | O que faz |
| --- | --- | --- |
| `DomainEvent` | `shared/events/base.py` | dataclass imutável com `event_name`, `version`, `event_id`, `occurred_at` e `payload()` serializável |
| `publish(event)` | `shared/events/bus.py` | grava `OutboxEvent` **na transação corrente**; fora de transação levanta `RuntimeError` (evento sem estado não existe) |
| `@subscribe(name)` | idem | registra handlers no `ready()` do app consumidor (`orders.handlers`, `payments.application.handlers`) |
| `relay_pending(dispatch)` | idem | `SELECT … FOR UPDATE SKIP LOCKED` dos não publicados; uma task por **(evento, handler)**; marca `published_at` |
| `deliver(event_id, handler)` | idem | cria `ProcessedEvent (event, handler)` (UNIQUE) e roda o handler **na mesma transação**: duplicata vira no-op |
| Tasks | `shared/events/tasks.py` | `events.relay_outbox` (Beat, 5 s), `events.deliver` (`acks_late`, retry exponencial, 8 tentativas), `maintenance.purge_published_events` (diária, 30 dias) |

Diferenças em relação à proposta:

- **Sem `attempts`/`last_error` no `OutboxEvent`.** O relay só encaminha; quem falha é o handler, e
  o retry fica na task `events.deliver` (Celery). Assim um handler com erro não segura os outros
  handlers do mesmo evento.
- **Dedup por handler, não por evento** (`ProcessedEvent`): um evento com dois consumidores é
  entregue a cada um exatamente uma vez em efeito.
- Eventos em uso: `payments.payment.approved`, `payments.refund.requested`,
  `payments.payment.refunded` (`docs/architecture/event-driven.md`). E-mails e notificações
  seguirão o mesmo `publish` quando existirem.

Testes: `tests/shared/test_outbox.py` (rollback não publica; relay sobreposto; reentrega
deduplicada) e os fluxos de `apps/orders/tests/integration/test_payments_api.py`, que drenam o
outbox com `shared.testing.events.drain_events()`. Validado por mutação (sem dedup → teste falha).

## Alternatives Considered

### Manter apenas `transaction.on_commit`

- Prós: simples, zero infraestrutura extra.
- Contras: perda silenciosa de eventos em falha entre commit e enfileiramento.
- Aceitável para: e-mails, analytics. Não aceitável para: refund, liberação de estoque, integrações.

### Publicar no broker dentro da transação

- Contras: evento publicado e transação revertida → consumidores reagem a algo que não aconteceu.

### Change Data Capture (Debezium lendo o WAL)

- Prós: sem polling, robusto.
- Contras: infraestrutura pesada (Kafka Connect etc.) — desproporcional.

### Two-phase commit (XA) entre PostgreSQL e RabbitMQ

- Contras: complexo, frágil, pouco suportado no ecossistema Celery.

## Consequences

### Positivas

- Nenhum evento de negócio perdido; atomicidade entre estado e evento.
- Reprocessamento possível (eventos ficam registrados).

### Negativas / custos

- Latência extra (intervalo do relay); mais uma tabela e um job periódico.
- Entrega at-least-once exige consumidores idempotentes (já é regra do projeto).
- Polling gera carga leve constante no banco (mitigada por índice parcial em
  `published_at IS NULL`).

- Na UI, o resultado chega com atraso de até um ciclo do relay (5 s): a tela do pedido faz
  polling enquanto há trabalho em background (`awaitsBackgroundWork`).
- Handlers não podem chamar I/O externo dentro da transação da entrega quando isso exigir lock
  longo: o estorno (`payments.refund.requested`) chama o gateway e só então grava o resultado.
