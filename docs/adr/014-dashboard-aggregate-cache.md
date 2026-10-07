# ADR-014: Cache por tempo (TTL) dos agregados do dashboard

- **Status:** Accepted
- **Data:** 2026-10-07
- **Decisores:** time OrderFlow (Phase 11)
- **Relacionados:** ADR-006 (Redis, uso restrito), `docs/domain/dashboard.md`

## Context

O dashboard mostra agregados por organização: pedidos recebidos, funil atual, faturamento
líquido (aprovado − estornado), ticket médio e estoque baixo, com comparação ao período anterior.
A tela atualiza a cada minuto, e várias pessoas da mesma organização podem tê-la aberta ao mesmo
tempo. O ADR-006 restringe o Redis: **dado financeiro só pode ser cacheado com estratégia explícita
aprovada em ADR**, e o padrão é invalidar no use case que altera o dado.

Medição com volume realista (organização com 200 mil pedidos, 500 mil no banco, 400 mil
pagamentos, 50 mil estornos; banco descartável, PostgreSQL 17):

| Cenário | hoje | 7 dias | 30 dias |
| --- | --- | --- | --- |
| Sem índices novos, sem cache | 220 ms | 227 ms | 253 ms |
| Com índices (`orders_org_submitted_idx`, `payments_org_revenue_idx`, `payments_org_refunded_idx`) | 35 ms | 39 ms | 61 ms |
| 30 requisições simultâneas (30 dias), sem cache | 449 ms no total | | |
| 30 requisições simultâneas (30 dias), cache de 60 s | 7 ms no total | | |

## Decision

**Índices resolvem a latência; um cache por tempo (60 s) limita a carga.** Os agregados são
cacheados por **organização + período** (`dashboard:v1:<org>:<período>`), com TTL de
`DASHBOARD_CACHE_SECONDS` (60) e **sem invalidação por evento**. A defasagem máxima (1 minuto) é
explícita na tela ("Atualizado às… · os números podem ter até 1 minuto de atraso").

- O cache guarda o payload completo da organização; as seções de dinheiro (`reports:financial`)
  e de estoque (`inventory:read`) são removidas **depois** de ler o cache, conforme quem pede.
- O cache é derivado e descartável: nada lê dele para decidir regra de negócio; a fonte da verdade
  continua no PostgreSQL (ADR-006 segue valendo para todo o resto).
- O frontend atualiza a cada 60 s — mais rápido só devolveria o mesmo número.

## Alternatives Considered

### Sem cache (só índices)

- Prós: números sempre atuais; nenhuma peça a mais.
- Contras: a carga cresce com o número de pessoas com a tela aberta (N consultas por minuto por
  organização), e o funil conta pedidos abertos, que crescem com a operação.
- Por que não: o custo de 1 minuto de defasagem é baixo para um painel; o teto de carga
  independente de usuários vale mais.

### Invalidação por evento (outbox) a cada pedido/pagamento

- Prós: números sempre frescos com cache.
- Contras: invalidaria a cada mudança de pedido — em horário de pico, o cache quase nunca seria
  usado; mais acoplamento (dashboard ouvindo eventos de três módulos).
- Por que não: complexidade sem ganho para um painel de tendência.

### Tabelas de agregados materializados (atualizadas por eventos ou job)

- Prós: leitura constante mesmo com milhões de pedidos.
- Contras: segunda fonte da verdade para dinheiro, reprocessamento, consistência.
- Por que não: com índices a consulta direta leva dezenas de ms; revisitar se passar de ~1 s.

## Consequences

### Positivas

- Latência baixa com índices; carga no banco limitada a ~1 cálculo por minuto por organização e
  período, qualquer que seja o número de pessoas olhando.
- Permissão aplicada sobre o cache compartilhado (testado: o vendedor nunca recebe a seção de
  dinheiro preenchida por um gerente).

### Negativas / custos aceitos

- Até 1 minuto de defasagem (comunicada na tela).
- Três índices novos (criados com `CREATE INDEX CONCURRENTLY` para não bloquear escritas no
  deploy).

### Quando revisitar

Se o cálculo sem cache passar de ~500 ms em alguma organização, ou se surgir indicador que exija
tempo real (aí: agregados materializados ou outro ADR).
