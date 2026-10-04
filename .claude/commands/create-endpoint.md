---
description: Fluxo completo para criar um endpoint REST — use case, endpoint via skill create-rest-endpoint, testes de integração, OpenAPI e revisões de segurança e domínio.
argument-hint: <module> <METHOD /api/v1/path> [descrição]
disable-model-invocation: true
---

# Criar endpoint: $ARGUMENTS

1. **Contexto**: leia `CLAUDE.md`, `docs/domain/<module>.md` e ADRs relevantes (ADR-012 se for
   criação de pedido/pagamento/refund; ADR-008 se tocar estoque).
2. **Regra de negócio**: identifique o use case/query. Se a regra não estiver documentada no doc de
   domínio, documente primeiro (e pergunte ao usuário se houver decisão de negócio em aberto).
3. **Implementação**: use a skill `create-rest-endpoint`.
4. **Testes**: use a skill `write-integration-tests` (e `write-unit-tests` para regras novas de domínio).
5. **Verificação**: `moon run backend:check`.
6. **Revisões**: rode as skills `review-security` e `review-domain` e corrija os achados críticos/altos.
7. **Resumo**: endpoint, permissões, códigos de erro, testes adicionados e impacto no frontend
   (tipos/composables a atualizar).
