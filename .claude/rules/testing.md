---
paths:
  - "backend/**/tests/**"
  - "backend/**/test_*.py"
  - "backend/conftest.py"
  - "frontend/**/*.spec.ts"
  - "frontend/**/*.test.ts"
  - "frontend/**/tests/**"
---

# Testes

- Backend: pytest + pytest-django + factory_boy + Faker. Frontend: Vitest + Vue Test Utils.
- Pirâmide: maioria unit (domínio puro, sem banco), depois integração (use case + PostgreSQL
  real, API), poucos E2E.
- Nomes descrevem comportamento: `test_cancel_paid_order_requests_refund`,
  `test_reserve_fails_when_available_is_lower_than_requested`.
- Arrange/Act/Assert visíveis. Um comportamento por teste.
- Factories em `apps/<module>/tests/factories.py`; nada de fixtures JSON gigantes.
- Banco de teste é **PostgreSQL** (nunca SQLite) — locks, constraints e isolamento importam.
- Testes de concorrência usam `@pytest.mark.django_db(transaction=True)` e threads/conexões
  reais; marcados com `@pytest.mark.concurrency`.
- Cada regra de negócio tem teste do caminho feliz **e** dos caminhos de erro (estado inválido,
  permissão negada, estoque insuficiente, idempotência).
- Integrações externas são testadas com os adapters fake (`FakePaymentGateway` etc.), nunca rede real.
- Não mockar o que pertence ao próprio módulo; mockar apenas fronteiras (gateways, relógio, Celery).
- Cobertura é consequência, não meta: priorize regras de domínio e caminhos críticos.
