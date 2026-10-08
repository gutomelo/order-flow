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
- Phase 6: removidos o lock do pedido, o lock do contador de números, a checagem do total esperado,
  o replay de idempotência, a cópia do endereço, o histórico de status e a checagem "só rascunho é
  editável" — cada um derruba ao menos um teste (o histórico, sete). No frontend, gerar uma chave de
  idempotência nova a cada tentativa faz o teste de retry falhar.
- Phase 7: removido o lock dos itens, o teste da última unidade **seguiu verde** — a disputa via
  `POST /orders` já era serializada pelo contador de números da organização. Reescrito para disputar
  via `POST /orders/{id}/reserve`; aí, sem o lock, os testes de última unidade e de deadlock falham, e
  travar os itens na ordem das linhas (em vez de por `id`) produz deadlock detectado pelo PostgreSQL.
  Sem o `lock_timeout`, o teste de `STOCK_BUSY` falha. Lição: confirme que o teste exercita o lock que
  diz proteger — outro lock no caminho pode mascarar a ausência dele.

- Phase 8: sem gravar a recusa na idempotência, sem estornar a aprovação que chega após o
  cancelamento, sem pedir estorno ao cancelar pedido pago, sem pular a expiração com cobrança no ar,
  sem a deduplicação do `ProcessedEvent` e sem o registro `IN_PROGRESS` antes da chamada ao
  gateway — cada um derruba um teste. Na reconciliação, tratar "provedor não conhece a cobrança"
  como "sem resposta" (backoff de horas) e vice-versa derrubam um teste cada; não limpar o
  `failure_reason` na nova tentativa de estorno também. No frontend, não trocar a chave após a
  recusa, trocar após falha de rede, oferecer cancelamento de pago com `orders:cancel`, permitir
  "tentar estorno" em pagamento manual e aceitar baixa sem referência derrubam um teste cada.
  O E2E com worker e Beat reais achou dois problemas que os testes não pegavam: a tela parava de
  atualizar entre a aprovação e a chegada do evento ao pedido, e "provedor indisponível" travava o
  pedido por horas (backoff aplicado a uma resposta definitiva).

- Phase 9: sem a baixa de estoque no despacho, sem o re-check de `SHIPPED` na segunda transação
  (o teste de concorrência pega), sem a checagem de transição depois da etiqueta (pedido
  cancelado no meio), sem o evento do rastreio, sem marcar a remessa na entrega manual, com o
  handler de entrega ignorando o estado e com erro de transportadora não tratado — cada um derruba
  um teste. Três mutações passaram na primeira rodada: a idempotência do provedor fake (o código de
  rastreio vem da chave, então só o relógio da entrega mostrava a diferença) e as permissões de
  `ship`/`confirm-delivery` (a matriz parava os papéis negados na separação). Os testes foram
  reescritos (relógio da entrega; cada ação negada no estado em que valeria) e passaram a pegar.
  Uma mutação equivalente ficou documentada: o retorno antecipado do rastreio para remessa já
  entregue só evita uma consulta — o re-check com lock garante o resultado. No frontend, ignorar a
  permissão, despachar sem confirmar, não aparar a observação, fila sem ordenação, rota sem
  permissão e erro do despacho fora do diálogo derrubam um teste cada.

- Phase 10: 20 mutações no backend (transição sem evento, rascunho cancelado avisando, ignorar o
  contato principal, envio sem checar status, erro do SMTP com a mensagem, nunca marcar `FAILED`,
  cancelamento sem o aviso de estorno, alerta enquanto o estoque continua baixo, ledger sem
  alerta, avisar usuário inativo, reset para conta inativa, reset sem encerrar sessões, token na
  query string, throttle errado, histórico sem escopo, e-mail sem máscara, reenvio sem checar
  convite pendente, criar sem senha sem convidar, `Message-ID` aleatório, aviso sem destinatário
  na fila) — todas detectadas; a do reset para conta inativa só depois de o teste olhar também os
  avisos criados (o envio já barrava, então só o e-mail não bastava). No frontend, o teste de
  "token fora da URL" era vazio (com histórico em memória `window.location` nunca muda) — a
  implementação passou a usar o router e o teste a olhar a rota. O E2E achou o que os testes não
  pegavam: `password: null` recusado pelo serializer (o teste omitia o campo) e o erro sumindo no
  campo escondido; e o RabbitMQ bloqueado por disco cheio, que o outbox atravessou sem perder nada.

- Phase 11: 12 mutações no backend (faturamento sem estornos, estornado fora do faturamento,
  período anterior sem deslocar, dias em UTC, "hoje" começando em UTC, cache sem organização,
  dinheiro não removido, estoque no ponto não contando, recentes invertidos, recusado como pago,
  estoque para quem não lê estoque, série sem barras vazias) — todas detectadas, duas só depois de
  ajustes: o helper do teste criava pagamento recusado **sem** data de conclusão (no sistema real a
  recusa grava a data), escondendo o caso; e faltava um pedido às 22h para separar dia do negócio de
  dia UTC. No frontend, 6 mutações detectadas. Medição de desempenho num banco descartável com
  500 mil pedidos (ADR-014). O E2E achou: texto de variação reprovado em contraste (cor de status em
  texto), frase sem sentido no "sem base" e rolagem horizontal no celular.

- Phase 12: 13 mutações no backend (pedido sem autor, resultado síncrono sem autor, retenção
  ignorando o prazo ou sem liberar o trigger, reserva entrando como estoque manual, ponto igual
  registrando, evento sem `request_id`, rótulo virando id, nova tentativa e falha da reconciliação
  fora da trilha, pagamento sem pedido relacionado, cancelamento como mudança comum, confirmação
  manual sem autor) e 7 no frontend — todas detectadas. O teste de retenção precisou ser
  transacional: `set_config(..., true)` vale até o fim da transação, e no teste comum (uma
  transação só) a permissão de apagar continuaria ligada — em produção a limpeza faz commit.

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
