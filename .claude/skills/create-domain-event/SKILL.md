---
name: create-domain-event
description: Cria um Domain Event e seus handlers no OrderFlow (evento imutável, payload serializável, despacho in_transaction ou after_commit, handlers idempotentes) e o registra no catálogo de eventos. Use quando uma mudança de estado precisar disparar efeitos em outros módulos.
argument-hint: <module> <EventName> [descrição]
---

# Criar Domain Event

Entrada: `$ARGUMENTS`

## 1. Justificar

Responda antes de criar:
- Quem consome o evento? Se o único consumidor é o próprio use case e o resultado é necessário na
  hora, **não é evento**: é uma chamada direta.
- O efeito precisa ser atômico com a mudança (`in_transaction`, ex.: auditoria crítica) ou pode ser
  eventual (`after_commit`, ex.: e-mail)?
- Perder este evento causaria inconsistência de negócio? Se sim, leia ADR-011 (Transactional Outbox)
  e sinalize ao usuário.

## 2. Implementar

Siga `.claude/templates/domain-event.md`:
- Classe no passado em `apps/<module>/domain/events.py`, `event_name = "<module>.<entity>.<action>"`,
  `version = 1`.
- Payload mínimo com primitivos (UUID/Decimal como string). Sem dados sensíveis.
- Publicação no use case via `shared.events.publish(...)` dentro da transação; o despacho
  `after_commit` é feito pela infraestrutura de eventos.
- Handlers no módulo **consumidor** (`apps/<consumer>/handlers.py`), idempotentes, registrados no
  `ready()` do app. Trabalho pesado vai para task Celery (`create-celery-task`).

## 3. Documentar

- Catálogo em `docs/architecture/event-driven.md` (evento, produtor, consumidores, modo).
- Tabela de eventos em `docs/domain/<module>.md`.

## 4. Testar

- Use case publica o evento com payload correto.
- Rollback da transação → evento `after_commit` **não** é despachado.
- Handler executado duas vezes com o mesmo `event_id` → efeito único.
