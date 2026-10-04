---
paths:
  - "backend/apps/*/api/**"
  - "backend/config/urls.py"
  - "backend/shared/pagination/**"
  - "backend/shared/permissions/**"
---

# API REST (DRF)

- Base `/api/v1/`. Recursos no plural, kebab-case: `/api/v1/stock-reservations`.
- Ações de domínio como endpoints explícitos: `POST /api/v1/orders/{id}/cancel`, `/pay`, `/ship`.
  Não modele ações como `PATCH status`.
- View fina: parse/validação de formato (serializer) → chamada ao use case → serialização da saída.
  Serializers de entrada e de saída separados quando os formatos divergirem.
- Status HTTP: 200 leitura/ação síncrona, 201 criação, 202 aceito para processamento assíncrono,
  204 sem corpo, 400 validação, 401 não autenticado, 403 sem permissão, 404 não encontrado
  (também para recurso fora do escopo do usuário), 409 conflito de estado/estoque/idempotência,
  422 regra de negócio violada, 429 throttling.
- Erros sempre no envelope:
  `{"error": {"code": "INSUFFICIENT_STOCK", "message": "Estoque insuficiente.", "details": {...}}}`.
  Erros de validação: `code = "VALIDATION_ERROR"`, `details.fields = {campo: [mensagens]}`.
- Toda coleção é paginada (paginação padrão do projeto), com filtros, busca e ordenação
  explicitamente permitidos (`ordering_fields` whitelist).
- `POST /orders`, `/payments`, `/refunds` exigem header `Idempotency-Key` (ADR-012).
- Todo endpoint tem `permission_classes` explícitas com permissões `resource:action` e
  queryset escopado ao usuário.
- drf-spectacular: anotar com `@extend_schema` quando a inferência não bastar (ações, erros,
  headers). O schema em `/api/schema/` é contrato com o frontend.
