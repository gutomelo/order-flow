# ADR-001: Modular Monolith como arquitetura inicial

- **Status:** Accepted
- **Data:** 2026-10-04
- **Relacionados:** ADR-002, ADR-005, ADR-011, `docs/architecture/overview.md`

## Context

O OrderFlow cobre vários subdomínios (identidade, catálogo, estoque, pedidos, preços, pagamentos,
envio, notificações, auditoria) com regras fortemente transacionais entre si: criar um pedido exige
validar cliente, calcular preço e reservar estoque de forma atômica.

Forças:
- equipe pequena (inicialmente uma pessoa) e projeto de portfólio que precisa ser executável
  localmente com um comando;
- o fluxo crítico (pedido + reserva de estoque) precisa de consistência forte;
- queremos demonstrar fronteiras de domínio claras e permitir evolução futura;
- custo operacional deve ser baixo (um deploy, um banco).

## Decision

Construir o backend como um **Modular Monolith**: um único projeto Django, um único deploy e um
único banco PostgreSQL, com módulos de negócio isolados em `backend/apps/<module>/`.

Regras de fronteira:
1. Cada módulo é dono das suas tabelas; somente ele escreve nelas.
2. Comunicação entre módulos: chamada à camada `application` do módulo dono (quando o chamador
   precisa do resultado) ou Domain Events (efeitos secundários).
3. `ForeignKey` entre módulos é permitida (integridade referencial vale mais que isolamento
   teórico neste estágio).
4. Fronteiras verificadas automaticamente por **import-linter** na tarefa `backend:check`.

## Alternatives Considered

### Microsserviços desde o início

- Prós: deploy e escala independentes; isolamento forte.
- Contras: transações distribuídas (sagas) para o fluxo mais crítico; infraestrutura de rede,
  observabilidade distribuída, versionamento de contratos; custo enorme para um time pequeno.
- Por que não: resolve problemas de escala organizacional que não temos e cria problemas de
  consistência que hoje são resolvidos com uma transação.

### Monolito Django tradicional (sem fronteiras)

- Prós: mais simples no início.
- Contras: acoplamento cresce sem controle (qualquer app importa qualquer model); regras se espalham;
  extrair um módulo depois fica caro.
- Por que não: não demonstra nem preserva fronteiras de domínio.

## Consequences

### Positivas

- Transações ACID para o fluxo de pedido + estoque.
- Um comando sobe tudo (`docker compose up`); debugging simples.
- Fronteiras explícitas e verificadas permitem extrair um módulo no futuro (ex.: `notifications`).

### Negativas / custos aceitos

- Escala é do monolito inteiro (mitigado: workers Celery escalam separadamente).
- Disciplina de fronteiras depende de convenção + import-linter; FKs entre módulos tornam uma
  extração futura mais trabalhosa.

### Quando revisitar

Quando um módulo tiver necessidade comprovada de escala, cadência de deploy ou time independentes,
ou quando o tempo de build/teste do monolito se tornar gargalo mensurável.
