---
paths:
  - "backend/apps/*/infrastructure/tasks/**"
  - "backend/apps/*/tasks.py"
  - "backend/config/celery.py"
  - "backend/shared/events/**"
---

# Celery e processamento assíncrono

- Task recebe **IDs** (string UUID), nunca objetos/models. Recarrega o estado do banco.
- Toda task é **idempotente**: executá-la duas vezes produz o mesmo resultado lógico
  (verificar estado antes de agir; usar chaves únicas no banco).
- Enfileirar somente após commit: `transaction.on_commit(lambda: task.delay(...))`.
- Erros transitórios (rede, timeout, 5xx da integração): `autoretry_for` + `retry_backoff=True`
  + `retry_jitter=True` + `max_retries` explícito. Erros permanentes (validação, 4xx, regra de
  negócio): não fazer retry; logar e registrar falha.
- `acks_late=True` para tasks que alteram estado (requer idempotência).
- Nome explícito e estável: `name="notifications.send_order_confirmation"`.
- Fila explícita por natureza: `default`, `notifications`, `integrations`, `maintenance`.
- Propagar `request_id`/`correlation_id` nos headers da task e no contexto de log.
- Tasks periódicas (Celery Beat) devem tolerar execução concorrente/atrasada (ex.: expiração de
  reservas usa `select_for_update(skip_locked=True)` e processa em lotes).
- Testes: testar a função de negócio diretamente; testar a task com `task.apply()` (eager local)
  e cenários de retry/idempotência.
