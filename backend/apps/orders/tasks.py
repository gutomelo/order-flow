from celery import shared_task

from apps.orders.application.commands.expiration import (
    cancel_stale_pending_orders as cancel_stale,
)
from apps.orders.application.commands.expiration import expire_due_orders


# acks_late: se o worker cair no meio, o lote é reentregue; cada pedido é revalidado com lock.
@shared_task(name="maintenance.expire_unpaid_orders", queue="maintenance", acks_late=True)
def expire_unpaid_orders() -> int:
    return expire_due_orders()


@shared_task(name="maintenance.cancel_stale_pending_orders", queue="maintenance", acks_late=True)
def cancel_stale_pending_orders() -> int:
    return cancel_stale()
