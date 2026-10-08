---
name: write-unit-tests
description: Escreve testes unitários no OrderFlow — regras de domínio, máquina de estados, cálculos de preço/desconto, políticas (pytest, sem banco) e composables/schemas/componentes do frontend (Vitest). Use após implementar ou alterar regras de negócio ou lógica de frontend.
argument-hint: <arquivo-ou-módulo-alvo>
---

# Escrever testes unitários

Alvo: `$ARGUMENTS`

## 1. Partir da especificação

Leia a regra em `docs/domain/` (ou a docstring/ADR). Teste o **comportamento especificado**, não a
implementação. Liste os cenários antes de escrever:
- caminho feliz;
- cada caminho de erro (exceção de domínio com `code` esperado);
- limites (0, 1, máximo, igual ao disponível, arredondamento de `Decimal`);
- transições permitidas **e** proibidas (tabela completa via `pytest.mark.parametrize`).

## 2. Backend (pytest)

- Sem banco quando possível: domínio puro recebe valores/dataclasses. Use `@pytest.mark.django_db`
  só se o alvo exigir.
- Local: `apps/<module>/tests/unit/test_<assunto>.py`.
- Nomes: `test_<comportamento>_when_<condição>`.
- Dinheiro: compare `Decimal("10.00")`, nunca float.
- Relógio: injete/congele tempo (ex.: expiração de reserva) em vez de `sleep`.

## 3. Frontend (Vitest)

- Composables com `QueryClient` de teste; mocks apenas na fronteira HTTP.
- Schemas Zod: entradas válidas e inválidas com mensagens esperadas.
- Componentes: comportamento visível (texto, estados, eventos emitidos), não detalhes internos.

## 4. Validar o teste

Quebre temporariamente a regra e confirme que o teste falha. Rode `moon run backend:test` ou
`moon run frontend:test`.
