# Domínio: Payments (Pagamentos)

> Implementado na Phase 8. Módulo com camadas (`api/`, `application/`, `domain/`,
> `infrastructure/`): integra um provedor externo, e o adapter do gateway é a fronteira testável.

## Responsabilidade

Registrar **cobranças e estornos** e conversar com o gateway. `payments` não conhece regras de
pedido: recebe `order_id` (opaco) e o valor, e informa o resultado por eventos. Quem decide o que o
pedido vira (`PAID`, `REFUNDED`...) é `orders`.

## Formas de pagamento

| Método | Como | Resultado |
| --- | --- | --- |
| `CARD` | cobrança no gateway com um **token** gerado pelo widget do provedor | `APPROVED`, `DECLINED` ou, em timeout, `PENDING` até a reconciliação |
| `MANUAL` | baixa feita pelo financeiro (boleto, PIX, transferência conciliados fora) | `APPROVED` na hora; exige referência (ex.: id da transação PIX) |

Webhooks de PIX/boleto ficam para quando houver gateway real (questão em aberto).

## Dados sensíveis

O OrderFlow **não recebe nem guarda dados de cartão**: no navegador, o widget do provedor gera um
token; o backend repassa o token ao gateway e **não o persiste** (nem em log). Do pagamento ficam
apenas valor, status, referência do provedor e motivo de recusa.

## Modelo

| Entidade | Campos principais |
| --- | --- |
| `Payment` | `order_id` (opaco), `order_reference` (ex.: `#000003`), `method`, `amount`, `currency`, `status`, `idempotency_key` (enviada ao gateway), `provider_reference`, `decline_reason`, `manual_reference`, `attempts`, `next_attempt_at`, `completed_at`, `created_by` |
| `Refund` | `payment`, `amount`, `status`, `idempotency_key`, `provider_reference`, `failure_reason`, `attempts`, `completed_at`, `requested_by` |

### Estados

| `Payment` | Próximos | | `Refund` | Próximos |
| --- | --- | --- | --- | --- |
| `PENDING` | `APPROVED`, `DECLINED`, `FAILED` | | `PENDING` | `SUCCEEDED`, `FAILED` |
| `APPROVED` | `REFUNDED` | | `FAILED` | `PENDING` (nova tentativa pelo financeiro) |
| `DECLINED`, `FAILED`, `REFUNDED` | — | | `SUCCEEDED` | — |

## Regras

| # | Regra | Garantida em |
| --- | --- | --- |
| P1 | No máximo **um** pagamento `APPROVED` por pedido (nunca cobrar duas vezes) | UNIQUE parcial |
| P2 | No máximo **um** pagamento `PENDING` por pedido (uma tentativa por vez) | UNIQUE parcial → `PAYMENT_IN_PROGRESS` |
| P3 | Valor = total do pedido (pagamento integral no MVP); `amount > 0` | `orders` + CHECK |
| P4 | Token de cartão não é persistido nem logado | serviço + revisão |
| P5 | Estorno só de pagamento `APPROVED`, sempre **total**; no máximo um estorno não falho por pagamento | serviço + UNIQUE parcial |
| P6 | Pagamentos e estornos nunca são removidos | `PROTECT` + sem endpoint de exclusão |
| P7 | Chamada ao gateway **fora** de transação com lock | `orders.PayOrder` (duas transações) |

## Gateway (`PaymentGateway`, porta em `domain/gateway.py`)

`charge`, `get_charge` (reconciliação), `refund`, `get_refund` — todas com **chave de
idempotência** própria do pagamento/estorno, para que repetir a chamada não cobre duas vezes.

`FakePaymentGateway` (`infrastructure/fake_gateway.py`, padrão em dev/teste): o resultado depende
do **token de teste**; o "lado do provedor" fica no cache (Redis em dev), como num provedor real.

| Token | Cobrança | Estorno |
| --- | --- | --- |
| `tok_approved` | aprovada | ok |
| `tok_declined` | recusada (`insufficient_funds`) | — |
| `tok_timeout` | o provedor aprova, mas a resposta não chega (timeout) | ok |
| `tok_unavailable` | provedor indisponível; nada é cobrado | — |
| `tok_refund_fails` | aprovada | estorno recusado pelo provedor |

## Reconciliação

`maintenance.reconcile_pending_payments` (Beat, a cada minuto): pagamentos `CARD` `PENDING` com
`next_attempt_at` vencido (a 1ª consulta sai 1 min depois da cobrança) consultam `get_charge` pela
chave de idempotência:

| Resposta do provedor | Resultado |
| --- | --- |
| Conhece a cobrança | `APPROVED`/`DECLINED` (+ evento) |
| Responde que **não** conhece a chave | `FAILED` na hora: nada foi cobrado, e o pedido pode ser pago de novo |
| Não responde à consulta | nova consulta com backoff exponencial (1, 2, 4… até 60 min); após `PAYMENT_RECONCILIATION_MAX_ATTEMPTS` (10) → `FAILED` |

Separar "não conhece" de "não respondeu" importa por causa da P2: com um `PENDING` vivo, o pedido
não aceita outra tentativa. Esperar o backoff inteiro (~5 h) quando o provedor já disse que não
cobrou bloquearia o cliente sem motivo (achado no E2E da Phase 8).

Estornos executam numa task (`RefundRequested` → handler) com retry exponencial para falha
transitória; recusa do provedor → `FAILED`, visível ao financeiro, que pode tentar de novo.

## Eventos (outbox, ADR-011)

| Evento | Quando | Consumidor |
| --- | --- | --- |
| `payments.payment.approved` | pagamento aprovado (síncrono, manual ou reconciliado) | `orders`: aplica o resultado (`PAID`, ou estorno se o pedido não pode mais ser pago) |
| `payments.refund.requested` | estorno criado | `payments`: executa no gateway (I/O fora da transação de quem pediu) |
| `payments.payment.refunded` | estorno concluído | `orders`: `CANCELLED → REFUNDED` |

## Casos de uso

| Use case | Endpoint | Permissão | Idempotente |
| --- | --- | --- | --- |
| Pagar com cartão | `POST /api/v1/orders/{id}/pay` (`orders`) | `payments:create` | `Idempotency-Key` |
| Registrar pagamento recebido | `POST /api/v1/orders/{id}/record-payment` (`orders`) | `payments:create` | `Idempotency-Key` |
| Listar pagamentos e estornos | `GET /api/v1/payments?status=&method=` | `payments:read` | — |
| Tentar estorno de novo | `POST /api/v1/refunds/{id}/retry` | `payments:refund` | `Idempotency-Key` |
| Confirmar estorno manual | `POST /api/v1/refunds/{id}/confirm` | `payments:refund` | `Idempotency-Key` |

## Erros de domínio

| Código | HTTP | Quando |
| --- | --- | --- |
| `PAYMENT_DECLINED` | 422 | Gateway recusou (`details.reason`); o pedido segue aguardando pagamento |
| `PAYMENT_IN_PROGRESS` | 409 | Já há uma cobrança pendente para o pedido |
| `ORDER_NOT_AWAITING_PAYMENT` | 409 | Pagamento de pedido fora de `AWAITING_PAYMENT` |
| `REFUND_NOT_RETRYABLE` | 409 | Nova tentativa de estorno que não está `FAILED` (ou é manual) |
| `REFUND_NOT_MANUAL` | 409 | Confirmação manual de estorno de cartão |

## Fora do escopo

Pagamento parcial e parcelado, estorno parcial, webhooks (PIX/boleto), múltiplas moedas, gateway
real e conciliação bancária automática.
