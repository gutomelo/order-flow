# Template: task Celery

```python
import structlog
from celery import shared_task

from shared.integrations.exceptions import PermanentIntegrationError, TransientIntegrationError

logger = structlog.get_logger(__name__)


@shared_task(
    name="notifications.send_order_confirmation",
    queue="notifications",
    acks_late=True,
    autoretry_for=(TransientIntegrationError,),
    retry_backoff=True,      # backoff exponencial
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
)
def send_order_confirmation(order_id: str, event_id: str) -> None:
    """Envia confirmação do pedido. Idempotente por (event_id, canal)."""
    if NotificationLog.objects.filter(event_id=event_id, channel="email").exists():
        logger.info("notifications.order_confirmation.skipped_duplicate", order_id=order_id)
        return

    try:
        ...  # carregar estado atual do banco pelo ID e executar
    except PermanentIntegrationError:
        # Falha permanente: não adianta tentar de novo. Registrar para análise/reprocessamento.
        logger.error("notifications.order_confirmation.failed_permanently", order_id=order_id)
        raise
```

## Enfileiramento

```python
transaction.on_commit(
    lambda: send_order_confirmation.delay(order_id=str(order.id), event_id=str(event.event_id))
)
```

## Checklist

- [ ] Argumentos são IDs/primitivos, nunca objetos
- [ ] Idempotente (verifica estado ou registro de execução antes de agir)
- [ ] Retry só para erros transitórios; backoff + jitter + `max_retries`
- [ ] Erro permanente registrado e não re-tentado
- [ ] Nome e fila explícitos
- [ ] Enfileirada via `transaction.on_commit`
- [ ] Logs estruturados com IDs (sem dados sensíveis)
- [ ] Testes: sucesso, duplicata, erro transitório (retry), erro permanente
