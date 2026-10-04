# ADR-006: Redis para cache e throttling (uso restrito)

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-005, ADR-008, ADR-012

## Context

Algumas leituras são caras e mudam pouco (catálogo, configurações, agregados de dashboard).
Endpoints sensíveis precisam de rate limiting compartilhado entre processos. Ao mesmo tempo, Redis é
frequentemente usado como "solução universal", criando uma segunda fonte da verdade difícil de
manter consistente.

## Decision

Usar **Redis** para:
1. **Cache** do Django (`django.core.cache.backends.redis.RedisCache`) em dados de leitura
   frequente e invalidação clara: catálogo, configurações, dashboards agregados (TTL curto).
2. **Throttling** do DRF (contadores compartilhados entre workers).
3. **Backend de resultados do Celery**, somente para tasks que realmente precisem de resultado.

**Não** usar Redis para:
- estoque, reservas ou qualquer dado financeiro (fonte da verdade é o PostgreSQL; cache só com
  estratégia explícita de invalidação aprovada em ADR);
- locks de estoque (o lock de linha do PostgreSQL já resolve, ADR-008);
- chaves de idempotência (persistidas no PostgreSQL na mesma transação do efeito, ADR-012);
- broker do Celery (RabbitMQ, ADR-005).

Toda entrada de cache tem chave versionada por módulo (`catalog:v1:product:<id>`), TTL explícito e
invalidação no use case que altera o dado (após o commit).

## Alternatives Considered

### Sem Redis (cache em memória local / banco)

- Contras: cache local não é compartilhado entre processos; throttling inconsistente.

### Memcached

- Contras: não serve como backend de resultados do Celery; menos versátil; ganho nenhum.

### Redis como "cola" para tudo (broker, locks, idempotência)

- Por que não: cria fontes da verdade paralelas e problemas de consistência que o PostgreSQL resolve
  transacionalmente.

## Consequences

### Positivas

- Ganho de performance onde importa, sem risco nos dados críticos.

### Negativas / custos aceitos

- Mais um serviço. Bugs de invalidação de cache possíveis (mitigados por TTL curto e escopo restrito).

### Quando revisitar

Se métricas mostrarem necessidade de cache em dados críticos, ou se o throttling exigir algoritmo
mais sofisticado.
