---
name: write-integration-tests
description: Escreve testes de integração no OrderFlow — use cases com PostgreSQL real, endpoints DRF (status, envelope de erro, permissões, IDOR), idempotência, rollback, concorrência de estoque e tasks Celery. Use após implementar use cases, endpoints ou fluxos transacionais.
argument-hint: <use-case-ou-endpoint>
---

# Escrever testes de integração

Alvo: `$ARGUMENTS`

## 1. Setup

- PostgreSQL real (o mesmo do `docker compose`), nunca SQLite.
- Factories do módulo (`apps/<module>/tests/factories.py`); crie as que faltarem.
- Local: `apps/<module>/tests/integration/`.

## 2. Use case

- Estado final do banco após sucesso (registros, status, `OrderStatusHistory`, `StockMovement`).
- **Rollback**: forçar falha no meio (ex.: gateway fake falhando) → nenhum estado parcial persiste.
- Eventos publicados apenas após commit (`django_capture_on_commit_callbacks`).

## 3. API

Para cada endpoint: 2xx com corpo esperado · 400 `VALIDATION_ERROR` · 401 · 403 · 404 para objeto
fora do escopo (IDOR) · 409/422 com `code` de domínio · envelope de erro no formato padrão ·
paginação/filtros quando lista.

## 4. Idempotência (pedido, pagamento, refund)

- Mesma `Idempotency-Key` + mesmo payload → mesma resposta, **um** registro criado.
- Mesma chave + payload diferente → 422 `IDEMPOTENCY_KEY_REUSED`.
- Requisição concorrente com a mesma chave em processamento → 409 `IDEMPOTENCY_REQUEST_IN_PROGRESS`.

## 5. Concorrência (estoque)

```python
@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_last_unit_is_never_sold_twice(): ...
```

Duas threads (cada uma com sua conexão; feche `connection` ao final da thread) disputando a última
unidade, sincronizadas com `threading.Barrier`. Esperado: exatamente um sucesso, um
`INSUFFICIENT_STOCK`, `reserved == 1`, invariantes do banco preservadas.

## 6. Celery

Executar a task com `.apply()`; testar duplicidade, retry em erro transitório e erro permanente.

Rode `moon run backend:test`.
