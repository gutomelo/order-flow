---
name: create-rest-endpoint
description: Cria um endpoint REST com DRF no OrderFlow seguindo os padrões do projeto — view fina, use case na application layer, permissões resource:action, queryset escopado, envelope de erro, paginação, idempotência quando aplicável e documentação OpenAPI. Use ao expor recursos ou ações de domínio na API.
argument-hint: <module> <METHOD /api/v1/path> [descrição]
---

# Criar endpoint REST

Entrada: `$ARGUMENTS`

## 1. Classificar o endpoint

- **Recurso** (listar/detalhar/criar/editar) ou **ação de domínio** (`POST /orders/{id}/cancel`)?
  Ações de domínio nunca viram `PATCH status`.
- Qual use case/query atende? Se não existe, crie em `application/` primeiro (a view não decide nada).
- Permissão necessária (`resource:action`). Se for nova, registre no catálogo de permissões de
  `apps/identity` e atribua aos roles adequados (ver `docs/architecture/security.md`).
- Exige `Idempotency-Key`? Obrigatório para criação de pedido, pagamento e refund (ADR-012).

## 2. Implementar

- Serializer de **entrada** com campos explícitos e validação de formato (tipos, limites).
  Serializer de **saída** separado se o formato divergir. Nunca `fields = "__all__"`.
- View: `permission_classes` explícitas; `get_queryset()` escopado ao usuário (anti-IDOR);
  `select_related`/`prefetch_related` para evitar N+1.
- Listagens: paginação padrão, `filterset_fields`/`search_fields`/`ordering_fields` em whitelist.
- Erros de domínio sobem como `DomainError` → o exception handler global gera o envelope.
- Status HTTP conforme `.claude/rules/backend-api.md`.
- `@extend_schema` com request, responses (incluindo erros 400/403/404/409/422) e headers
  (`Idempotency-Key`).

## 3. Testar (`write-integration-tests`)

Mínimo: sucesso; validação inválida (400); sem autenticação (401); sem permissão (403); objeto de
outro escopo (404); regra de negócio violada (409/422); idempotência quando aplicável.

## 4. Verificar

`moon run backend:check`. Confirme que o endpoint aparece corretamente em `/api/docs/`.
