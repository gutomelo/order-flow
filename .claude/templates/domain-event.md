# Template: Domain Event

## Definição (`apps/<module>/domain/events.py`)

```python
from dataclasses import dataclass

from shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderCancelled(DomainEvent):
    """Pedido cancelado. Consumidores: inventory (libera reserva), payments (refund se pago),
    notifications, audit."""

    event_name = "orders.order.cancelled"
    version = 1

    order_id: str          # UUID como string — payload sempre serializável
    previous_status: str
    reason: str
    cancelled_by: str
```

`DomainEvent` (em `shared/events`) fornece `event_id`, `occurred_at` (UTC) e `correlation_id`.

## Handler

```python
from shared.events import subscribe


@subscribe(OrderCancelled, mode="after_commit")
def send_cancellation_notification(event: OrderCancelled) -> None:
    # Handler só enfileira; o trabalho pesado é a task (idempotente).
    send_order_cancelled_email.delay(order_id=event.order_id, event_id=event.event_id)
```

Modos de despacho:

| Modo | Quando usar | Exemplo |
| --- | --- | --- |
| `in_transaction` | O efeito precisa ser atômico com a mudança | `AuditLog` de operação crítica |
| `after_commit` | Efeito secundário; pode ser assíncrono | e-mail, analytics, documentos |

## Checklist

- [ ] Nome no passado, específico (`OrderCancelled`, não `OrderUpdated`)
- [ ] `event_name` estável `module.entity.action` e `version`
- [ ] Payload mínimo, primitivo, sem dados sensíveis
- [ ] Handlers idempotentes (usar `event_id` para deduplicar quando houver efeito externo)
- [ ] Documentado em `docs/architecture/event-driven.md` (catálogo) e no doc do domínio
- [ ] Testes: evento publicado no use case; handler idempotente; nada publicado em rollback
