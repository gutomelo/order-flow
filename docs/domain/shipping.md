# Domínio: Shipping (Envio)

> Implementado na Phase 9. Módulo com `application/`, `domain/` e `infrastructure/` — sem `api/`:
> as ações (separar, despachar, confirmar entrega) são do ciclo do pedido e ficam nos endpoints de
> `orders`. O adapter da transportadora é a fronteira testável.

## Responsabilidade

Registrar a **remessa** de um pedido e conversar com a transportadora (etiqueta e rastreio).
`shipping` não conhece regras de pedido: recebe `order_id` (opaco), a referência e o destino, e
informa a entrega por evento. Quem decide o que o pedido vira (`SHIPPED`, `DELIVERED`) é `orders`,
e quem baixa o estoque é `inventory` — `orders` coordena as três coisas na mesma transação.

## Decisões de produto (Phase 9)

| Pergunta | Decisão | Por quê |
| --- | --- | --- |
| Remessas parciais? | **Não**: uma remessa por pedido | mesma lógica tudo-ou-nada da reserva; parcial exige estados intermediários e consumo parcial |
| Como o pedido chega a entregue? | **Rastreio da transportadora + confirmação manual** | rastreio cobre o caso comum; retirada no balcão e frota própria não têm rastreio |
| Devolução (`DELIVERED → REFUNDED`)? | **Depois** | o roadmap da Phase 9 termina em `DELIVERED` |
| Frete cobrado? | **Não**: `shipping_total` continua 0 | cotar frete mexe em preço, total e pagamento já aprovado |

## Modelo

| Entidade | Campos principais |
| --- | --- |
| `Shipment` | `order_id` (opaco), `order_reference`, `carrier`, `tracking_code`, `status`, `shipped_at`, `shipped_by`, `delivered_at`, `delivery_source` (`PROVIDER`/`MANUAL`), `delivered_by`, `delivery_note`, `last_checked_at`, `next_check_at` |

| Status | Próximo |
| --- | --- |
| `IN_TRANSIT` | `DELIVERED` |
| `DELIVERED` | — |

## Regras

| # | Regra | Garantida em |
| --- | --- | --- |
| S1 | Uma remessa por pedido | UNIQUE `order_id`; chave de idempotência da etiqueta = id do pedido |
| S2 | Código de rastreio único por transportadora | UNIQUE (`carrier`, `tracking_code`) |
| S3 | Entregue ⇔ tem `delivered_at` e origem da confirmação; em trânsito ⇔ não tem | CHECK |
| S4 | Chamada à transportadora **fora** de transação com lock | `orders.ship_order` (etiqueta antes, gravação depois) |
| S5 | Despachar baixa o estoque na mesma transação que cria a remessa e muda o pedido | `orders.ship_order` → `inventory.consume_reservations` (`SALE`) |
| S6 | Remessa nunca é removida nem dada como perdida automaticamente | sem endpoint de exclusão; rastreio sem limite de tentativas |

## Transportadora (`ShippingProvider`, porta em `domain/provider.py`)

`create_shipment(idempotency_key, reference, destination) → Label(carrier, tracking_code)` e
`track(tracking_code) → Tracking(delivered_at)`. Sem resposta conclusiva → `ProviderUnavailable`.

`FakeShippingProvider` (`infrastructure/fake_provider.py`, padrão em dev/teste): etiqueta
determinística pela chave (repetir devolve a mesma, sem reiniciar o relógio da entrega) e entrega
`FAKE_SHIPPING_TRANSIT_MINUTES` (2) depois do despacho. O "lado do provedor" fica no cache.

## Despacho (`ShipOrder`, coordenado por `orders`)

```text
(sem lock)  pedido READY_TO_SHIP? → etiqueta na transportadora (idempotente pelo pedido)
Tx          trava o pedido → ainda READY_TO_SHIP? → consume_reservations (SALE)
            → Shipment IN_TRANSIT → pedido SHIPPED
```

- Transportadora indisponível → `503 SHIPPING_PROVIDER_UNAVAILABLE`; nada mudou, despachar de
  novo é seguro (mesma etiqueta).
- Pedido cancelado enquanto a etiqueta era gerada → `409 INVALID_ORDER_TRANSITION`, nada sai do
  estoque; a etiqueta fica sem uso na transportadora (log `orders.shipping.label_unused`).
- Dois despachos simultâneos → um grava, o outro encontra `SHIPPED` e devolve o pedido (teste de
  concorrência).

## Rastreio

`maintenance.track_shipments` (Beat, a cada minuto, fila `integrations`): remessas `IN_TRANSIT`
com `next_check_at` vencido consultam `track`. Entregue → `DELIVERED` (`PROVIDER`) + evento
`shipping.shipment.delivered` (outbox). Ainda em trânsito ou transportadora fora do ar → próxima
consulta em `SHIPMENT_TRACKING_INTERVAL_MINUTES` (60; 1 em dev). Intervalo fixo, sem backoff: a
entrega leva dias e uma consulta por hora não pesa.

## Confirmação manual

`POST /orders/{id}/confirm-delivery` (`orders:ship`), com observação opcional (ex.: "recebido
por Maria"). Marca a remessa `MANUAL` e o pedido `DELIVERED` na mesma transação — por isso **não**
publica evento. Se o rastreio chegar depois, encontra a remessa entregue e não faz nada; se chegar
antes, a confirmação manual é idempotente.

## Eventos (outbox, ADR-011)

| Evento | Quando | Consumidor |
| --- | --- | --- |
| `shipping.shipment.delivered` | rastreio informou a entrega | `orders`: `SHIPPED → DELIVERED` (idempotente por estado) |

## Erros de domínio

| Código | HTTP | Quando |
| --- | --- | --- |
| `SHIPPING_PROVIDER_UNAVAILABLE` | 503 | Transportadora não respondeu ao pedir a etiqueta |
| `RESERVATION_NOT_CONFIRMED` | 409 | Despacho sem reserva paga (`inventory`; inalcançável pelo fluxo normal) |

## Questões em aberto

- Etiqueta sem uso quando o pedido é cancelado durante o despacho: com transportadora real que
  cobra por etiqueta, chamar o cancelamento da etiqueta (`cancel_shipment` na porta).
- Remessas parciais, cotação e cobrança de frete, devolução pós-entrega, extravio (hoje a
  logística investiga e confirma à mão), webhooks de rastreio.
