# Domínio: Notifications (Avisos por e-mail)

> Implementado na Phase 10. Módulo com `api/` (histórico do pedido), `application/` e `domain/`.
> Não tem `infrastructure/`: o adapter de e-mail é o backend de e-mail do Django (ver
> [Envio](#envio-e-entrega)). Ninguém depende de `notifications`: ele só **reage a eventos**.

## Responsabilidade

Transformar eventos de negócio em e-mails, enviá-los fora das transações de negócio e guardar o
histórico (enviado, falhou, sem destinatário). Não decide nada sobre pedido, estoque ou usuário:
lê os dados atuais pela camada pública de cada módulo (`application`/`selectors`).

## Decisões de produto (Phase 10)

| Pergunta | Decisão | Por quê |
| --- | --- | --- |
| Quem do cliente recebe? | **Contato principal com e-mail**; sem ele, o e-mail do cadastro do cliente; sem nenhum, o aviso fica registrado como **sem destinatário** | um destinatário claro; nenhum aviso some em silêncio |
| Quais avisos? | Ciclo do pedido ao cliente, estoque baixo, convite e redefinição de senha | alertas internos (estorno recusado, reserva expirada) ficaram fora desta fase |
| Canal | **Só e-mail**, com histórico visível no pedido | notificação no app (sino) é bem maior e não tinha pergunta de negócio |
| Dev | **Mailpit** no Docker Compose (SMTP + caixa de entrada web) | mesmo caminho SMTP de produção; console só esconderia problemas |

## Avisos

| Tipo | Gatilho (evento) | Destinatário |
| --- | --- | --- |
| `ORDER_CONFIRMED` | `orders.order.status_changed` → `AWAITING_PAYMENT` | cliente |
| `ORDER_PAID` | → `PAID` | cliente |
| `ORDER_SHIPPED` | → `SHIPPED` (transportadora e rastreio) | cliente |
| `ORDER_DELIVERED` | → `DELIVERED` | cliente |
| `ORDER_CANCELLED` | → `CANCELLED`, exceto de `DRAFT`; avisa do estorno se o pedido estava pago | cliente |
| `ORDER_REFUNDED` | → `REFUNDED` | cliente |
| `STOCK_LOW` | `inventory.stock.low` | usuários ativos com `inventory:update` (RBAC, não papel fixo) |
| `USER_INVITATION` | `identity.user.invited` | o convidado |
| `PASSWORD_RESET` | `identity.password_reset.requested` | o próprio usuário |

Sem aviso ao cliente: pedido parado em `PENDING` por falta de estoque (avisa quando reservar),
separação (`PROCESSING`, `READY_TO_SHIP`), reserva expirada e rascunho descartado. A regra fica em
`domain/policies.order_notification_kind` (tabela testada). O motivo do cancelamento é interno e
**não** vai para o e-mail.

## Modelo

| Entidade | Campos principais |
| --- | --- |
| `Notification` | `kind`, `status`, `source_event_id`, `reference_id` (pedido, item de estoque ou usuário), `recipient_email`, `recipient_name`, `subject`, `context` (parâmetros não sensíveis), `attempts`, `last_error` (tipo do erro), `sent_at` |

| Status | Significado |
| --- | --- |
| `PENDING` | na fila de envio (ou aguardando nova tentativa) |
| `SENT` | entregue ao servidor de e-mail |
| `FAILED` | `NOTIFICATIONS_MAX_ATTEMPTS` (5) tentativas esgotadas |
| `SKIPPED` | sem destinatário (cliente sem e-mail; conta desativada antes do envio) |

O **corpo não é guardado**: é montado na hora do envio a partir dos dados atuais
(`application/rendering.py`, templates em `templates/notifications/email/`). Assim e-mails de
segurança nunca deixam o link com token no banco, e os demais não duplicam dados pessoais.

## Regras

| # | Regra | Garantida em |
| --- | --- | --- |
| N1 | Um aviso por (evento, destinatário): reentrega do evento não duplica | `ProcessedEvent` do outbox + UNIQUE (`source_event_id`, `recipient_email`) |
| N2 | Enviado ⇔ tem `sent_at` | CHECK |
| N3 | Só "sem destinatário" fica sem e-mail | CHECK |
| N4 | E-mail nunca sai de dentro de uma transação que pode ser desfeita | handler só cria o registro; envio em task após o commit |
| N5 | Dois workers nunca enviam o mesmo aviso ao mesmo tempo | `SELECT … FOR UPDATE SKIP LOCKED` + status `PENDING` |
| N6 | Endereço e token nunca vão para log | logs só com ids; `last_error` guarda o tipo do erro (a mensagem do SMTP traz o endereço) |

## Envio e entrega

```text
evento (outbox) → handler: Notification PENDING (mesma transação da entrega do evento)
                → on_commit: task notifications.send (fila notifications)
                → lock + monta o e-mail com os dados atuais → SMTP → SENT
falha transitória (SMTPException, OSError) → attempts+1 → retry 30 s, 1, 2, 4 min → FAILED na 5ª
pendente parado há 10 min (enfileiramento perdido) → maintenance.requeue_stale_notifications (Beat)
```

- **Exatamente uma vez não existe com SMTP.** Se o processo morrer entre o envio e gravar `SENT`,
  a varredura reenviará; o `Message-ID` é o id do aviso (`<id@domínio>`), e clientes de e-mail
  descartam a duplicata.
- **Adapter:** `EMAIL_BACKEND` do Django — SMTP (Mailpit em dev, provedor real em produção),
  `locmem` nos testes, console como padrão seguro. O roadmap previa um `EmailProvider`/
  `ConsoleEmailProvider` próprios; o Django já oferece exatamente essa porta com adapters, então
  criar outra seria abstração sem problema novo (ver `docs/architecture/backend.md`).
- Datas no fuso `NOTIFICATIONS_TIME_ZONE` (America/Sao_Paulo) e dinheiro em pt-BR
  (`application/formatting.py`): o e-mail não tem o fuso nem o locale de um navegador.

## Casos de uso / API

| Use case | Endpoint | Permissão |
| --- | --- | --- |
| Avisos do pedido | `GET /api/v1/orders/{id}/notifications` (destinatário mascarado `ma***@empresa.com`) | `orders:read` |

Pedido de outra organização devolve lista vazia (escopo por organização, anti-IDOR).

## Questões em aberto

- Alertas internos: estorno recusado → financeiro; reserva expirada → vendedor.
- E-mail em HTML (hoje só texto), preferências de recebimento por contato, notificação no app.
- Webhook de bounce/entrega do provedor real (hoje `SENT` = aceito pelo SMTP).
