# Regras de arquitetura (sempre carregadas)

## Modular Monolith

- Cada módulo de negócio é um Django app em `backend/apps/<module>/` e é dono das suas tabelas.
- Outro módulo **pode**: chamar `apps.<module>.application` (use cases e queries públicas), reagir
  a Domain Events de `apps.<module>.domain.events`, declarar `ForeignKey` para models do módulo dono.
- Outro módulo **não pode**: escrever em models de outro módulo, importar `infrastructure/` ou
  `api/` de outro módulo, ou depender de detalhes internos de `domain/` além de eventos e tipos
  públicos. Essas fronteiras são verificadas por `import-linter` (contratos em `backend/pyproject.toml`).
- `backend/shared/` contém apenas código transversal sem regra de negócio de um módulo específico.
  Se algo em `shared/` conhece "pedido" ou "estoque", está no lugar errado.

## Camadas (quando o módulo justificar)

```text
api/            DRF: serializers, views, permissions, urls  → fino, sem regra de negócio
application/    use cases (commands), queries, orquestração, transações
domain/         entidades/regras/políticas/estados/eventos/exceções → sem Django HTTP, sem Celery
infrastructure/ repositories, adapters de integrações, tasks Celery
models.py       models Django (persistência)
```

- Dependências apontam para dentro: `api → application → domain`; `infrastructure` implementa
  portas definidas em `domain`/`application`.
- `domain/` pode usar tipos simples, `Decimal`, `dataclasses`, enums. Evite importar o ORM no
  domínio puro; quando a regra opera sobre um model, prefira funções/políticas que recebem valores.
- Módulos simples (ex.: `suppliers`) podem ter apenas `models.py`, `api/`, `services.py`, `tests/`.
  **Não crie diretórios vazios.**

## Anti-overengineering

Antes de criar interface, repository, factory, adapter, base class, service, DTO, mapper ou evento,
responda: *qual problema concreto isto resolve agora?* Sem resposta objetiva → não crie.
Repository só para query complexa, isolamento de domínio, integração externa ou testabilidade real.

## God classes

Um service/use case = uma intenção de negócio (`PlaceOrder`, `CancelOrder`, `ReserveStock`).
Se uma classe começa a coordenar estoque, pagamento, e-mail e envio ao mesmo tempo, extraia:
o use case orquestra, cada módulo decide sua parte, efeitos secundários viram Domain Events.

## Decisões

Mudança que contradiz ou estende um ADR exige novo ADR ou atualização do existente (`/create-adr`).
