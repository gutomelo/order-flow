# Domínio: Audit (Trilha de auditoria)

> Implementado na Phase 12. Módulo `api/` → `application/` → `domain/`; **só reage a eventos**
> (nenhum módulo depende dele) e só lê os outros pela camada pública (contratos do
> import-linter).

## Responsabilidade

Responder "quem fez o quê, quando e por quê" sobre pedidos, dinheiro e estoque, com o antes e
depois do que mudou. Registro imutável: nada no sistema altera ou apaga um registro (só a limpeza
de retenção, ver abaixo).

## Decisões de produto (Phase 12)

| Pergunta | Decisão | Por quê |
| --- | --- | --- |
| Escopo | **Pedidos e dinheiro** + **estoque manual** | onde estão as operações críticas; usuários/acesso e cadastros ficaram para depois |
| Como grava | **Por evento no outbox** (ADR-011) | o evento nasce na transação da mudança (nunca se perde); ninguém depende de audit; falha na auditoria não desfaz a operação |
| Detalhe | **Antes/depois dos campos** + motivo + `request_id` | permite investigar sem cruzar tabelas |
| Retenção | **5 anos, configurável** (`AUDIT_RETENTION_DAYS`) | prazo usual de registros comerciais/fiscais; limpeza mensal |

> Mudança em relação ao desenho original (`domain-model.md`): ele previa handlers síncronos
> `in_transaction` para operações críticas. Com o outbox, o evento já é atômico com a mudança —
> a garantia "nunca perde" vem dele, e o registro aparece segundos depois (o relay roda a cada
> 5 s) sem acoplar todos os módulos a `audit`.

## O que é auditado

| Ação | Evento de origem | Autor |
| --- | --- | --- |
| `ORDER_CREATED`, `ORDER_STATUS_CHANGED`, `ORDER_CANCELLED` | `orders.order.status_changed` (toda transição, em `transition()`) | quem fez; sistema em expiração, entrega pelo rastreio e estorno concluído |
| `PAYMENT_STARTED`, `PAYMENT_APPROVED`, `PAYMENT_RECORDED` (baixa manual), `PAYMENT_DECLINED`, `PAYMENT_FAILED`, `PAYMENT_REFUNDED` | `payments.payment.status_changed` | quem pediu a cobrança (resultado síncrono); sistema na reconciliação |
| `REFUND_REQUESTED`, `REFUND_RETRIED`, `REFUND_COMPLETED`, `REFUND_FAILED` | `payments.refund.status_changed` | quem pediu/confirmou; sistema quando o provedor responde |
| `STOCK_RECEIVED`, `STOCK_ADJUSTED`, `STOCK_TRANSFERRED` | `inventory.stock.changed` (só movimentos manuais) | quem fez |
| `REORDER_POINT_CHANGED` | `inventory.reorder_point.changed` (só quando o valor muda) | quem fez |

Reserva, liberação e venda (baixa no despacho) **não** viram registro de estoque: são efeito do
pedido, já auditado pelas transições dele, e estão no ledger (`StockMovement`).

## Modelo

| Campo | Conteúdo |
| --- | --- |
| `action`, `entity_type` (`ORDER`, `PAYMENT`, `REFUND`, `STOCK_ITEM`), `entity_id` | o quê e em quê |
| `entity_label` | nome legível **no momento** ("#000003", "COLA · CD-SP") — renomear o produto não reescreve o passado |
| `order_id` | pedido relacionado (pagamentos e estornos inclusos): "tudo sobre o pedido X" |
| `actor` | quem fez; `null` = sistema |
| `changes` | `{"status": ["PAID", "CANCELLED"], "amount": "13.00"}` — só campos não sensíveis |
| `reason` | motivo do cancelamento/ajuste, referência da baixa manual, motivo de recusa/falha |
| `occurred_at` / `recorded_at` | quando aconteceu (do evento) / quando foi gravado |
| `request_id` | liga o registro à requisição (mesmo `X-Request-ID` da resposta e dos logs) |
| `source_event_id` | evento de origem; **UUID simples, sem FK**: a limpeza do outbox (30 dias) não apaga auditoria |

## Regras

| # | Regra | Garantida em |
| --- | --- | --- |
| A1 | Um registro por evento, mesmo com reentrega | `ProcessedEvent` + UNIQUE `source_event_id` |
| A2 | Registro não é alterado nem apagado | trigger `audit_log_append_only` (UPDATE/DELETE → erro) |
| A3 | Só a retenção apaga, só o que passou do prazo | a limpeza liga `audit.allow_purge` com `set_config(..., true)` — vale só na própria transação |
| A4 | Nada sensível nos registros | eventos levam só ids, valores e motivos; nunca token, senha, cartão ou dados de contato |
| A5 | Cada organização vê só a própria trilha | `TenantScopedQuerysetMixin` |

## Retenção

`maintenance.purge_expired_audit_logs` (Beat, dia 1 de cada mês, 03:30): apaga em lotes de 5 mil
os registros com `occurred_at` além de `AUDIT_RETENTION_DAYS` (1825). Lotes curtos para não manter
uma transação longa na tabela.

## API

| Endpoint | Permissão | Filtros |
| --- | --- | --- |
| `GET /api/v1/audit-logs` | `audit:read` (ADMIN, MANAGER) | `action` (vários), `entity_type`, `entity_id`, `order_id`, `actor`, `occurred_after`, `occurred_before`, `search` (rótulo e motivo); mais recentes primeiro |

Somente leitura: não há criar, editar nem apagar pela API (405).

## Questões em aberto

- Usuários e acesso (convite, papel, ativação, senha, login) — `security.md` prevê
  `USER_PERMISSION_CHANGED`; ficou fora do escopo desta fase.
- Cadastros e preços (clientes, produtos, tabelas de preço).
- `request_id` nas ações do sistema (tasks Celery não propagam o id da requisição de origem —
  correlation id ponta a ponta é da Phase 13).
- Particionamento por mês se o volume crescer; exportação para auditoria externa.
