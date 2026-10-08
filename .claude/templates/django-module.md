# Template: módulo Django

Escolha o **nível** pela complexidade real do módulo. Comece pelo menor nível que resolve o problema
e evolua quando a complexidade aparecer — nunca crie pastas vazias.

## Nível 1 — CRUD com regras simples (ex.: `suppliers`, `customers` no início)

```text
apps/<module>/
├── __init__.py
├── apps.py
├── models.py
├── services.py          # operações de escrita com regra (se houver)
├── selectors.py         # leituras reutilizáveis (se houver)
├── api/
│   ├── __init__.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── migrations/
└── tests/
    ├── __init__.py
    ├── factories.py
    └── test_api.py
```

## Nível 2 — domínio rico (ex.: `orders`, `inventory`, `payments`)

```text
apps/<module>/
├── apps.py
├── models.py                 # ou models/ quando houver muitos models
├── api/
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py        # só se houver permissão de objeto específica
│   └── urls.py
├── application/
│   ├── commands/             # um arquivo por use case: place_order.py
│   └── queries/              # leituras complexas
├── domain/
│   ├── events.py             # Domain Events do módulo
│   ├── exceptions.py         # erros com code estável
│   ├── state_machine.py      # se houver ciclo de vida
│   └── policies.py           # regras/strategies
├── infrastructure/
│   ├── tasks.py              # tasks Celery
│   └── <adapter>.py          # adapters de integração (se houver)
├── migrations/
└── tests/
    ├── factories.py
    ├── unit/
    └── integration/
```

## Esqueletos

### `apps.py`

```python
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"
    label = "orders"

    def ready(self) -> None:
        # Registra handlers de Domain Events do módulo (import com efeito colateral intencional).
        from apps.orders import handlers  # noqa: F401
```

### Use case (`application/commands/<use_case>.py`)

```python
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from shared.events import publish


@dataclass(frozen=True)
class CancelOrderCommand:
    order_id: UUID
    requested_by: UUID
    reason: str


class CancelOrder:
    """Cancela um pedido, libera a reserva de estoque e solicita refund quando já pago."""

    def execute(self, command: CancelOrderCommand) -> Order:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=command.order_id)
            transition = order.transition_to(OrderStatus.CANCELLED, reason=command.reason)
            # ... persistir, registrar histórico, liberar reserva via application do inventory
            publish(OrderCancelled.from_order(order, reason=command.reason))
        return order
```

### Exceção de domínio (`domain/exceptions.py`)

```python
from shared.exceptions import DomainError


class InvalidOrderTransition(DomainError):
    code = "INVALID_ORDER_TRANSITION"
    http_status = 409
    default_message = "Esta transição de status não é permitida."
```

Após criar: registrar em `INSTALLED_APPS`, incluir `api/urls.py` em `config/urls.py` sob
`/api/v1/`, adicionar contrato no import-linter, criar `docs/domain/<module>.md` a partir de
`.claude/templates/domain-doc.md`.
