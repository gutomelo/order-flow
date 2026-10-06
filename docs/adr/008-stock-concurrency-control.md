# ADR-008: Controle de concorrência de estoque com lock pessimista

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-004, `docs/domain/inventory.md`, `docs/domain/orders.md`

## Context

Cenário obrigatório: `available = 1`; os clientes A e B confirmam pedidos da mesma unidade ao mesmo
tempo. Sem controle, ambas as transações leem `available = 1`, ambas reservam e o sistema vende a
mesma unidade duas vezes (*lost update*).

Particularidades do nosso caso:
- um pedido tem **várias linhas**; a reserva é tudo-ou-nada;
- a disputa é **alta exatamente nos itens mais vendidos** (pouco estoque, muitos pedidos);
- toda alteração gera um `StockMovement` com o saldo resultante, que precisa ser coerente;
- `READ COMMITTED` (padrão do PostgreSQL) não impede *lost update* em leitura-depois-escrita.

## Decision

**Lock pessimista de linha** com `select_for_update()` dentro de `transaction.atomic()`, mais
**constraints no banco** como última defesa:

1. O use case `ReserveStock` abre a transação, ordena os `StockItem` envolvidos por `id` e os
   bloqueia com `SELECT ... FOR UPDATE` **nessa ordem** (ordem determinística evita deadlock entre
   pedidos com os mesmos produtos em ordens diferentes).
2. Com as linhas bloqueadas, o domínio verifica `available >= quantity` para **todas** as linhas;
   se alguma falhar, levanta `InsufficientStock` e a transação inteira faz rollback.
3. Atualiza `reserved` (via `F()`), cria `StockReservation` e `StockMovement(type=RESERVATION)`.
4. `CheckConstraint`s `reserved >= 0`, `on_hand >= 0` e `reserved <= on_hand` garantem que, mesmo com
   bug no código, o banco rejeita o estado inválido.
5. `lock_timeout` configurado na transação (ex.: 3 s) para não acumular conexões presas; timeout vira
   erro `STOCK_BUSY` (HTTP 409, re-tentável pelo cliente).
6. Teste de concorrência obrigatório (threads + `transaction=True`) para o cenário da última unidade
   e para deadlock com linhas em ordens opostas.

## Alternatives Considered

### Lock otimista (coluna `version` + retry)

- Prós: sem bloqueio; ótimo com baixa disputa.
- Contras: com alta disputa (nosso caso nos itens populares) gera muitos conflitos e retries;
  o retry de um pedido multi-linha é mais complexo; latência imprevisível.
- Por que não: otimiza o caso sem disputa, que já é rápido; piora o caso crítico.

### UPDATE condicional atômico (`UPDATE ... SET reserved = reserved + q WHERE on_hand - reserved >= q`)

- Prós: um único statement, sem lock explícito, excelente para uma linha.
- Contras: para várias linhas exige verificar `rowcount` de cada update e fazer rollback manual;
  não fornece o snapshot do saldo para o `StockMovement` sem leitura adicional.
- Por que não: válido e mais rápido para item único; mantido como otimização possível se métricas
  mostrarem contenção (registrar em novo ADR).

### Isolamento `SERIALIZABLE`

- Contras: falhas de serialização exigem retry de toda a transação, inclusive de partes não
  relacionadas a estoque; custo global.

### Lock distribuído no Redis

- Por que não: cria segunda fonte de verdade, depende de TTL/relógio e não protege contra escrita
  direta no banco. O lock de linha do PostgreSQL já é o mecanismo correto.

## Consequences

### Positivas

- Impossível vender a mesma unidade duas vezes (garantido pelo lock **e** pelas constraints).
- Comportamento previsível sob alta disputa: as requisições fazem fila na linha.

### Negativas / custos aceitos

- Transações que tocam o mesmo item serializam; a transação de reserva deve ser **curta** (nada de
  chamadas externas, e-mails ou pagamentos dentro dela).
- Requer disciplina de ordem de lock em todo código que bloqueia `StockItem`.

### Riscos e mitigação

- Deadlock → ordem determinística + `lock_timeout` + teste dedicado.
- Hot row em item muito popular → monitorar tempo de espera de lock; alternativa de UPDATE
  condicional documentada acima.

### Implementação (Phase 4)

A Phase 4 aplicou a decisão a recebimentos, ajustes e transferências por meio de um único ledger
(`apps/inventory/application/ledger.py`), antes de existirem reservas:

- **Ordem global de locks:** depósitos (`FOR SHARE`, ordenados por `id`) → `StockItem`
  (`FOR UPDATE`, ordenados por `id`). O `FOR SHARE` deixa movimentações no mesmo depósito em
  paralelo, mas serializa com a inativação (`FOR UPDATE`), que exige saldo zerado. Há SQL manual,
  parametrizado, porque o ORM não expõe `FOR SHARE`.
- Itens ausentes são criados com `bulk_create(ignore_conflicts=True)` antes do lock, para que dois
  recebimentos concorrentes do mesmo produto não disputem o `INSERT`.
- Como as linhas estão bloqueadas, o saldo novo é calculado em Python e gravado como valor absoluto
  (equivalente a `F()` sob lock), o que dá `on_hand_after`/`reserved_after` exatos no movimento.
- `available` é uma `GeneratedField` persistida; os movimentos são append-only por trigger.
- `lock_timeout` + `STOCK_BUSY` ficam para a Phase 7 (reservas), quando a disputa por item passa
  a ser real; até lá as transações são curtas e não há I/O externo dentro delas.

### Implementação (Phase 7)

- Reserva e liberação em `apps/inventory/application/commands/reservations.py`, chamadas por
  `orders` dentro da transação do pedido. Ordem global: **pedido → depósito (`FOR SHARE`) →
  `StockItem` (por `id`) → `StockReservation`**.
- `lock_timeout` por transação com `SELECT set_config('lock_timeout', %s, true)` (o `SET LOCAL`
  não aceita parâmetro); SQLSTATE `55P03` vira `STOCK_BUSY`. Configurável em
  `STOCK_LOCK_TIMEOUT_MS`.
- Achado dos testes de mutação: removendo o lock dos itens, o teste da última unidade **continuou
  verde** quando a disputa era via `POST /orders` — toda submissão já trava o contador de números
  da organização (Phase 6). Os testes passaram a disputar via `POST /orders/{id}/reserve`, que não
  passa pelo contador; aí o lock dos itens é a única proteção e a mutação falha como deveria.
- Reservas `ACTIVE` vencidas são liberadas pelo job de `orders` com `skip_locked`.

### Quando revisitar

Se métricas mostrarem p95 de espera por lock relevante em itens específicos, ou se a reserva passar
a envolver múltiplos depósitos com alocação automática.
