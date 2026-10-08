# ADR-005: RabbitMQ como broker e Celery para processamento assíncrono

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-006, ADR-011, `docs/architecture/event-driven.md`

## Context

Várias operações não devem bloquear a requisição HTTP: e-mails, notificações, geração de documentos,
chamadas a integrações externas (pagamento/frete) sujeitas a lentidão, expiração periódica de
reservas e relatórios. Essas operações precisam de retry com backoff, tolerância a falhas do worker
e agendamento periódico.

## Decision

- **Celery** como framework de tarefas; **Celery Beat** para tarefas periódicas.
- **RabbitMQ** como broker: entrega com acknowledgement, persistência de mensagens, filas nomeadas
  e roteamento; maduro com Celery.
- Filas separadas por natureza: `default`, `notifications`, `integrations`, `maintenance` — uma
  integração lenta não atrasa e-mails nem a expiração de reservas.
- Políticas (detalhadas em `.claude/rules/async-tasks.md`): tasks idempotentes, argumentos = IDs,
  `acks_late` em tasks que alteram estado, retry só para erros transitórios com backoff exponencial
  e jitter, enfileiramento via `transaction.on_commit`.
- Resultados de tasks ignorados por padrão (`task_ignore_result`); quando necessário, backend de
  resultados no Redis (ADR-006).
- Flower opcional no Docker Compose para inspeção local.

## Alternatives Considered

### Redis como broker

- Prós: um serviço a menos.
- Contras: semântica de entrega mais fraca (visibility timeout, risco de reentrega/perda em falhas),
  menos recursos de roteamento.
- Por que não: entrega confiável é mais importante que economizar um container.

### Dramatiq / RQ

- Prós: APIs mais simples.
- Contras: ecossistema e reconhecimento menores; Beat/agendamento exigem peças extras.

### Kafka

- Por que não: é um log de eventos para streaming em escala; desproporcional para filas de tarefas
  de um monolito modular.

## Consequences

### Positivas

- Requisições rápidas; falhas de integração isoladas e re-tentáveis.
- Base para eventos assíncronos entre módulos.

### Negativas / custos aceitos

- Mais um serviço para operar (RabbitMQ) e monitorar.
- Consistência eventual para efeitos secundários.
- Janela de perda entre commit e enfileiramento (processo cai após o commit) — avaliada no ADR-011.

### Quando revisitar

Se houver necessidade de replay de eventos/stream (considerar log de eventos) ou se o volume tornar
o RabbitMQ um gargalo.
