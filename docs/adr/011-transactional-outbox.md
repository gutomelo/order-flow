# ADR-011: Transactional Outbox para eventos críticos

- **Status:** Proposed
- **Data:** 2026-10-04
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

## Decision (proposta)

Adotar o **Transactional Outbox** quando o primeiro evento **com consequência de negócio** for
assíncrono (previsto na Phase 6–8: pedidos e pagamentos). Até lá, usar `on_commit`.

Desenho proposto:
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

### Quando decidir

Antes de implementar o primeiro handler assíncrono que altere estado de negócio em outro módulo.
A decisão final muda este ADR para `Accepted` (ou `Rejected` com justificativa).
