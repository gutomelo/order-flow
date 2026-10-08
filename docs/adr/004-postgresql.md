# ADR-004: PostgreSQL como banco principal e guardião de invariantes

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-008, ADR-011, ADR-012, `.claude/rules/database.md`

## Context

O sistema lida com estoque, dinheiro e estados de pedido. Bugs de aplicação, condições de corrida
ou scripts manuais não podem levar a estoque negativo, reservas maiores que o físico ou pedidos
duplicados. Precisamos de transações ACID, locking de linha, constraints declarativas e bom suporte
no Django.

## Decision

Usar **PostgreSQL** como única fonte da verdade, explorando seus recursos para proteger invariantes:

- **Constraints**: FKs (`PROTECT` em dados históricos/financeiros), `UNIQUE` (inclusive parciais),
  `CHECK` (ex.: `on_hand >= 0`, `reserved >= 0`, `reserved <= on_hand`, `total >= 0`).
- **Transações e locking**: `transaction.atomic()` + `SELECT ... FOR UPDATE` para estoque (ADR-008);
  `SKIP LOCKED` para jobs em lote.
- **Isolamento**: `READ COMMITTED` (padrão do PostgreSQL) combinado com locks explícitos onde há
  disputa; evitamos `SERIALIZABLE` global pelo custo de retries.
- **Tipos**: `NUMERIC` para dinheiro, `timestamptz` (UTC) para datas, UUID para IDs públicos,
  `JSONB` apenas para dados sem regra (ex.: `details` de auditoria, payload de eventos).
- **Colunas geradas** (`GeneratedField` do Django) para valores derivados que precisam ser
  filtráveis/indexáveis, como `available = on_hand - reserved` (ver `docs/domain/inventory.md`).
- Testes de integração e concorrência sempre contra PostgreSQL real.

## Alternatives Considered

### MySQL/MariaDB

- Contras: suporte a CHECK constraints e índices parciais historicamente mais limitado; menor
  alinhamento com recursos que queremos (JSONB, `SKIP LOCKED` maduro, colunas geradas no Django).

### SQLite em testes

- Contras: semântica de locking e constraints diferente; testes de concorrência não significam nada.
- Por que não: testes passariam em cenários que falham em produção.

## Consequences

### Positivas

- Invariantes protegidas mesmo contra bugs e acesso direto ao banco.
- Concorrência correta com ferramentas padrão.

### Negativas / custos aceitos

- Lógica duplicada intencionalmente (domínio dá a mensagem; banco é a última defesa).
- Testes mais lentos que SQLite (mitigado: unit tests de domínio não usam banco).

### Quando revisitar

Se volume de leitura analítica exigir réplica de leitura ou armazenamento analítico separado.
