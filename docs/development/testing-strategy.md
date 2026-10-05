# Estratégia de testes

## Pirâmide

```text
          E2E            poucos: fluxo de pedido ponta a ponta (Playwright, após Phase 6)
       ─────────
      Integração         use cases + PostgreSQL real, API (DRF), concorrência, Celery
   ────────────────
         Unit            maioria: domínio puro, máquina de estados, pricing, schemas, composables
```

| Nível | Ferramentas | Banco | Velocidade | Foco |
| --- | --- | --- | --- | --- |
| Unit (backend) | pytest | não | ms | regras de domínio, cálculos, transições |
| Integração (backend) | pytest-django, factory_boy, Faker | PostgreSQL | s | use cases, constraints, transações, API, permissões |
| Concorrência | pytest-django `transaction=True`, threads | PostgreSQL | s | locks, corridas, deadlock |
| Unit (frontend) | Vitest, Vue Test Utils | — | ms | composables, schemas Zod, componentes, formatação |
| E2E | Playwright (avaliar) | ambiente completo | min | fluxo crítico do usuário |

## Organização

```text
backend/apps/<module>/tests/
├── factories.py
├── unit/                 # sem banco
└── integration/          # @pytest.mark.django_db
backend/tests/            # transversais: arquitetura (import-linter), contrato OpenAPI, matriz RBAC
frontend/src/modules/<feature>/tests/
```

Marcadores pytest: `unit`, `integration`, `concurrency`, `slow`. A CI roda todos.

## Regras

- Banco de teste é **PostgreSQL**. SQLite proibido (semântica de locks e constraints diferente).
- Testes descrevem comportamento (`test_cancel_paid_order_requests_refund`).
- Teste deve falhar se a regra quebrar — validar quebrando a regra ao escrever o teste.
- Mockar apenas fronteiras: gateways (usar fakes), relógio, envio de tasks. Nunca mockar o próprio
  domínio.
- Adapters fake (`FakePaymentGateway`, `FakeShippingProvider`, `ConsoleEmailProvider`) são
  configuráveis para aprovar, recusar, falhar transitoriamente ou dar timeout.
- Contrato de portas: a mesma suíte de testes roda contra o fake e (quando existir) o adapter real
  em modo sandbox — garante LSP.
- Tempo: congelar/injetar relógio para expirações; nunca `sleep`.
- Cobertura é indicador, não meta. Prioridade: domínio e caminhos críticos (pedido, estoque,
  pagamento, autorização).

## Cenários obrigatórios

| # | Cenário | Nível | Módulo |
| --- | --- | --- | --- |
| T1 | Criação de pedido com sucesso (status, totais, linhas, histórico, reserva, eventos) | integração | orders |
| T2 | Criação sem estoque → 409 `INSUFFICIENT_STOCK`, nada persistido | integração | orders/inventory |
| T3 | **Concorrência**: `available = 1`, dois pedidos simultâneos → um sucesso, um 409 | concorrência | inventory |
| T4 | Deadlock: dois pedidos com os mesmos produtos em ordens opostas concluem sem deadlock | concorrência | inventory |
| T5 | Reserva de estoque: `reserved` e movimento `RESERVATION` corretos | integração | inventory |
| T6 | Expiração de reserva: job libera estoque, reserva `EXPIRED`, pedido volta a `PENDING` | integração | orders/inventory |
| T7 | Liberação de estoque no cancelamento (`RELEASE`) | integração | inventory |
| T8 | Transições válidas (tabela completa, parametrizado) | unit | orders |
| T9 | Transições inválidas (todas as não listadas) → `INVALID_ORDER_TRANSITION` | unit | orders |
| T10 | Cancelamento antes e depois do pagamento (refund solicitado) | integração | orders/payments |
| T11 | Pagamento aprovado → `PAID`, reserva `CONFIRMED` | integração | payments/orders |
| T12 | Pagamento recusado → `PaymentFailed`, pedido segue `AWAITING_PAYMENT` | integração | payments |
| T13 | Pagamento aprovado após expiração da reserva (re-reserva ou refund automático) | integração | orders/payments |
| T14 | Refund → `PaymentRefunded` → pedido `REFUNDED` | integração | payments/orders |
| T15 | Autorização: matriz role × endpoint; acesso a objeto fora do escopo → 404 | integração | todos |
| T16 | Idempotência: mesma chave + mesmo payload → mesma resposta, um registro; payload diferente → 422 | integração | shared/orders/payments |
| T17 | Rollback: falha no meio do use case não deixa estado parcial | integração | orders |
| T18 | Tasks Celery: sucesso, duplicada (efeito único), retry em erro transitório, falha permanente | integração | notifications/payments |
| T19 | Constraints do banco rejeitam estado inválido (`reserved > on_hand`) mesmo burlando o domínio | integração | inventory |
| T20 | Ajuste de estoque que deixaria `on_hand < reserved` → `INVALID_ADJUSTMENT` | unit/integração | inventory |
| T21 | Totais do pedido e arredondamento de `Decimal` | unit | orders/pricing |
| T22 | Envelope de erro padrão em 400/401/403/404/409/422/500 (sem stack trace) | integração | shared |

## Validar que o teste testa (mutação manual)

Teste que passa de primeira merece desconfiança. Para regras críticas, remova a regra
temporariamente e confirme que o teste **falha** (e falha rápido):

- Phase 2: sem o lock da organização, o teste de "último ADMIN" continuava passando — a corrida não
  era reproduzida. Foi reescrito com uma barreira entre "contar" e "gravar".
- Phase 3: sem a regra de ciclo de categorias, a suíte **travava** em vez de falhar, revelando
  laços sem proteção na leitura da árvore. As leituras passaram a tolerar ciclos.
- Phase 4: removidos um a um o `FOR SHARE` no depósito, o `select_for_update` dos itens e o
  `ON CONFLICT DO NOTHING` — cada teste de concorrência correspondente falhou. A primeira tentativa
  de quebrar a **ordem** dos locks não provou nada (a ordem continuava global); refeita como
  "origem → destino", o PostgreSQL detectou o deadlock e o teste falhou, como esperado. No
  frontend, enviar o saldo antigo como `expected_on_hand` após um conflito e mostrar o erro de
  inativação como toast (atrás do `<dialog>` modal) fazem os testes falharem.
- Phase 5: sem o lock no segmento (ao atribuir **ou** ao inativar) e sem o lock no cliente (papéis
  de endereço), os testes de concorrência falham; sem a promoção de papel e sem o filtro por cliente
  nos recursos aninhados (IDOR), os testes de API falham. No frontend, sem a invalidação em
  `onSettled` e sem o foco no primeiro campo inválido, os testes falham.

## Teste de concorrência — esqueleto

```python
@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_last_unit_is_never_sold_twice(stock_item_with_one_unit, two_customers):
    barrier = threading.Barrier(2)
    results: list[str] = []

    def place(customer):
        try:
            barrier.wait()
            PlaceOrder().execute(build_command(customer, stock_item_with_one_unit, qty=1))
            results.append("ok")
        except InsufficientStock:
            results.append("insufficient")
        finally:
            connection.close()  # cada thread usa a própria conexão

    threads = [threading.Thread(target=place, args=(c,)) for c in two_customers]
    for t in threads: t.start()
    for t in threads: t.join()

    assert sorted(results) == ["insufficient", "ok"]
    stock_item_with_one_unit.refresh_from_db()
    assert stock_item_with_one_unit.reserved == 1
```

## Execução

```bash
moon run :test                # tudo
moon run backend:test         # backend (requer docker compose up -d postgres redis rabbitmq)
moon run frontend:test
moon run :test --affected     # apenas projetos afetados
cd backend && uv run pytest -m concurrency    # filtrar por marcador
```

Comando Claude Code: `/run-tests [all|backend|frontend|affected|caminho]`.
