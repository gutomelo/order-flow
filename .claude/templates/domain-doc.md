# Domínio: <Módulo>

> Fonte da verdade das regras de negócio de `<module>`. Atualize no mesmo PR que mudar uma regra.

## Responsabilidade

<O que este módulo decide e o que ele NÃO decide.>

## Linguagem ubíqua

| Termo (código) | Significado |
| --- | --- |
| `TermInEnglish` | Definição em português |

## Modelo

<Entidades, value objects, relacionamentos. Diagrama Mermaid `classDiagram` se ajudar.>

## Invariantes

| # | Invariante | Garantida em |
| --- | --- | --- |
| I1 | <regra> | domínio + CHECK constraint |

## Estados e transições (se houver)

<Tabela de transições permitidas + diagrama `stateDiagram-v2`.>

## Casos de uso

| Use case | Permissão | Idempotente? | Eventos emitidos |
| --- | --- | --- | --- |
| `DoSomething` | `resource:action` | sim/não | `SomethingHappened` |

## Eventos

| Evento | Quando | Payload | Consumidores |
| --- | --- | --- | --- |

## Erros de domínio

| Código | HTTP | Quando |
| --- | --- | --- |

## Fluxos alternativos

<Falhas, expiração, cancelamento, indisponibilidade de integração.>

## Questões em aberto

-
