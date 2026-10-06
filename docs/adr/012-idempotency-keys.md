# ADR-012: Idempotency-Key persistida no PostgreSQL

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-004, ADR-006, `docs/domain/orders.md`

## Context

Redes falham. Um cliente que envia `POST /orders` e não recebe resposta (timeout, queda de conexão,
duplo clique) vai repetir a requisição. Sem proteção: pedidos duplicados, estoque reservado em dobro,
cobrança dupla.

Operações afetadas: `POST /api/v1/orders`, `POST /api/v1/orders/{id}/pay` (ou `/payments`),
`POST /api/v1/payments/{id}/refunds`.

## Decision

Exigir o header **`Idempotency-Key`** (UUID gerado pelo cliente por *intenção*) nessas operações e
persistir o registro **no PostgreSQL, na mesma transação do efeito**:

Tabela `idempotency_record`:
`key`, `scope` (usuário + operação), `request_fingerprint` (hash do método, path e corpo
normalizado), `status` (`IN_PROGRESS`, `COMPLETED`), `response_status`, `response_body`,
`created_at`, `expires_at`. Restrição `UNIQUE (scope, key)`.

Fluxo:
1. Sem header → `400 IDEMPOTENCY_KEY_REQUIRED`.
2. Insere registro `IN_PROGRESS` (o `UNIQUE` resolve corrida entre duas requisições iguais).
3. Se já existe:
   - `COMPLETED` + mesmo fingerprint → devolve a resposta armazenada (mesmo status e corpo);
   - fingerprint diferente → `422 IDEMPOTENCY_KEY_REUSED`;
   - `IN_PROGRESS` → `409 IDEMPOTENCY_REQUEST_IN_PROGRESS`.
4. Executa o use case; no mesmo commit grava a resposta e `COMPLETED`.
5. Falha com rollback → o registro também é revertido; o cliente pode tentar de novo com a mesma chave.
6. Expiração (ex.: 24 h) e limpeza periódica via Celery Beat.

Implementação como componente reutilizável em `shared/` (decorator/mixin de view), não espalhada
pelos módulos.

## Alternatives Considered

### Chaves no Redis

- Prós: rápido, TTL nativo.
- Contras: não é atômico com a transação do pedido: commit no banco + falha ao gravar no Redis (ou o
  inverso) reabre a duplicidade; perda de dados do Redis reabre a janela.
- Por que não: o objetivo é exatamente atomicidade com o efeito.

### Deduplicação por regras de negócio (ex.: "mesmo cliente + mesmos itens em 1 min")

- Contras: heurística; bloqueia pedidos legítimos repetidos e não cobre todos os casos.

### Idempotência apenas no frontend (desabilitar botão)

- Necessária para UX, insuficiente: não cobre retries de rede nem clientes de API.

## Consequences

### Positivas

- Retries seguros; mesma resposta lógica para a mesma intenção.
- Garantia transacional (sem janela entre efeito e registro).

### Negativas / custos aceitos

- Uma escrita extra por operação protegida; tabela que precisa de limpeza.
- Clientes precisam gerar e reutilizar a chave corretamente (documentado no OpenAPI e implementado
  no cliente HTTP do frontend).
- Respostas armazenadas não devem conter dados sensíveis.

### Implementação (Phase 6)

- Componente em `shared/idempotency` (app Django com a tabela `idempotency_record`) e o decorator
  `@idempotent("orders.place")` nas views. O escopo é (usuário, operação, chave).
- Operações de **uma** transação (como `POST /orders`): o registro nasce e conclui no mesmo commit.
  Uma segunda requisição com a mesma chave **espera** no índice único até a primeira terminar e
  recebe a resposta gravada (header `Idempotent-Replayed: true`). `IN_PROGRESS` visível para outros
  só existirá em operações de várias transações (pagamento, Phase 8).
- Só respostas 2xx são gravadas: erro de domínio desfaz tudo e a chave pode ser reenviada.
- Limpeza diária via Celery Beat (`maintenance.purge_expired_idempotency_records`).
- Frontend: a chave é por **conteúdo** (`useIdempotencyKey`): repetir o mesmo pedido reaproveita a
  chave; mudar o conteúdo gera outra.

### Quando revisitar

Se outras operações precisarem de idempotência (ex.: ajustes de estoque via integração) ou se o
volume tornar a tabela um gargalo.
