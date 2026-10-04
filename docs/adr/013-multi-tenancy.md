# ADR-013: Multi-tenancy com banco compartilhado e escopo explícito por organização

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-001, ADR-004, ADR-007, `docs/domain/identity.md`, `docs/architecture/security.md`

## Context

O OrderFlow será oferecido como SaaS: várias empresas (organizações) usam a mesma instalação.
Cada organização tem seus próprios usuários, clientes, produtos, estoque e pedidos, e **nenhum dado
pode vazar entre organizações** — é o pior defeito possível em um SaaS B2B, pior que indisponibilidade.

Forças:
- um único deploy e um único banco (ADR-001, ADR-004) — custo operacional baixo;
- dezenas a milhares de organizações pequenas/médias, não poucas gigantes;
- todo módulo de negócio é afetado; a decisão precisa ser tomada antes da primeira tabela de negócio
  (Phase 3);
- o mecanismo precisa ser verificável por teste, não apenas por disciplina.

## Decision

**Banco e schema compartilhados, com coluna `organization_id` em toda tabela de negócio e escopo
explícito em toda consulta.**

1. `Organization` (módulo `identity`) é o tenant. Cada `User` pertence a **exatamente uma**
   organização (superusuários da plataforma são a única exceção — `CHECK` no banco).
2. Toda tabela de negócio herda de `shared.tenancy.TenantScopedModel`, que adiciona
   `organization` (FK `PROTECT`, indexada). O model alvo é configurado em
   `settings.TENANT_MODEL = "identity.Organization"` — mesmo padrão de `AUTH_USER_MODEL`, para que
   `shared/` não importe `apps/`.
3. **O tenant vem sempre do usuário autenticado** (`request.user.organization_id`), nunca de header,
   subdomínio, corpo da requisição ou claim do JWT.
4. Escopo **explícito**: views usam `TenantScopedQuerysetMixin` (filtra `get_queryset()` pela
   organização do usuário e preenche `organization` na criação); use cases recebem
   `organization_id` no command. Não há filtro mágico por thread-local.
5. Restrições de unicidade de negócio passam a ser **por organização**
   (ex.: `UNIQUE (organization_id, sku)`).
6. Objeto de outra organização é tratado como inexistente: **404**, nunca 403.
7. Rede de segurança automatizada: um teste de arquitetura falha se algum model de `apps/` não
   tiver `organization` (lista de exceções explícita e justificada).
8. Organização inativa bloqueia login e invalida o acesso em andamento (a autenticação verifica
   `organization.is_active` a cada requisição).

## Alternatives Considered

### Schema por tenant (ex.: django-tenants)

- Prós: isolamento forte no banco; consultas não precisam filtrar.
- Contras: migrations rodam N vezes; milhares de schemas degradam o PostgreSQL e o planner;
  relatórios cross-tenant e ferramentas comuns ficam difíceis; acopla o projeto a uma biblioteca
  que reescreve o roteamento de conexão.
- Por que não: o custo operacional cresce com o número de clientes, e o nosso cenário é "muitos
  tenants pequenos".

### Banco por tenant

- Prós: isolamento máximo, backup/restore por cliente.
- Contras: provisionamento, conexões e migrations multiplicados; desproporcional para o produto.

### Filtro implícito (manager com thread-local / contextvar do tenant atual)

- Prós: impossível "esquecer" o filtro em consultas comuns.
- Contras: comportamento mágico; falha silenciosa em tasks Celery, comandos e testes quando o
  contexto não está definido; `Model.objects` passa a significar coisas diferentes conforme o
  contexto — difícil de revisar.
- Por que não: preferimos escopo visível no código, verificado por testes e revisão
  (`security-reviewer`).

### Row-Level Security do PostgreSQL

- Prós: defesa no próprio banco, independente de bugs da aplicação.
- Contras: exige definir o tenant por conexão (`SET app.current_org`), cuidado com pool de
  conexões, migrations e superusuário que ignora RLS.
- Decisão: **não agora**; é a evolução natural como defesa em profundidade quando houver dados de
  clientes reais (registrar em novo ADR).

### Usuário em várias organizações (membership N:N)

- Prós: consultores/contadores que atendem várias empresas.
- Contras: troca de organização ativa na sessão, permissões por membership, tokens por tenant.
- Por que não agora: nenhum requisito do MVP; a FK direta pode evoluir para `Membership`.

## Consequences

### Positivas

- Um banco, uma migration, operações simples; consultas cross-tenant de plataforma continuam possíveis.
- Isolamento verificável: mixin único, teste de arquitetura e testes de API de acesso cruzado.

### Negativas / custos aceitos

- Todo model e toda query de negócio carregam `organization_id` (índices compostos começando
  pela organização).
- O isolamento depende da aplicação; um `Model.objects.get(id=...)` sem escopo em código novo é
  um vazamento — mitigado por mixin, revisão e testes, e futuramente por RLS.
- E-mail de usuário é único na plataforma inteira (login sem escolher organização).

### Quando revisitar

Primeiro cliente com exigência contratual de isolamento físico, organizações muito grandes
(sharding), ou necessidade de usuários em várias organizações.
