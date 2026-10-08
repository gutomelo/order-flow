---
name: create-celery-task
description: Cria uma task Celery no OrderFlow com idempotência, retry com backoff exponencial e jitter, separação entre falha transitória e permanente, fila explícita e enfileiramento pós-commit. Use para e-mails, notificações, integrações externas, expiração de reservas, relatórios e reprocessamentos.
argument-hint: <module> <task_name> [descrição]
---

# Criar task Celery

Entrada: `$ARGUMENTS`

## 1. Justificar a assincronia

A operação é secundária, lenta, depende de integração externa ou é periódica? Se o usuário precisa
do resultado na resposta HTTP, ela **não** deve ser task.

## 2. Implementar

Siga `.claude/templates/celery-task.md` e `.claude/rules/async-tasks.md`:
- Arquivo `apps/<module>/infrastructure/tasks.py` (ou `tasks.py` em módulo simples).
- `name="<module>.<task_name>"`, fila adequada (`default`, `notifications`, `integrations`,
  `maintenance`).
- Argumentos = IDs como string. Recarregar estado do banco.
- Idempotência explícita: verificar estado atual ou registro de execução antes de agir.
- `autoretry_for` apenas exceções transitórias; `retry_backoff=True`, `retry_jitter=True`,
  `max_retries` definido. Falha permanente: logar, registrar e não re-tentar.
- `acks_late=True` se a task altera estado.
- Enfileirar com `transaction.on_commit(...)`.
- Task periódica: registrar no schedule do Celery Beat (`config/celery.py`), processar em lotes,
  `select_for_update(skip_locked=True)` para tolerar execuções sobrepostas.

## 3. Testar

Sucesso; execução duplicada (efeito único); erro transitório dispara retry; erro permanente não
re-tenta; lógica de negócio testada sem Celery (chamando a função/serviço diretamente).

## 4. Documentar

Se for periódica ou consumir evento, atualize `docs/architecture/event-driven.md`.
