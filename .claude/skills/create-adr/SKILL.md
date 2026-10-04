---
name: create-adr
description: Cria um Architecture Decision Record (ADR) no OrderFlow em docs/adr com Context, Decision, Alternatives Considered e Consequences, numerado sequencialmente e indexado. Use quando uma decisão for estrutural, difícil de reverter, introduzir tecnologia ou contrariar um ADR existente.
argument-hint: <título da decisão>
---

# Criar ADR

Decisão: `$ARGUMENTS`

## 1. Verificar necessidade e conflitos

- Leia `docs/adr/README.md`. Já existe ADR sobre o tema? Se a nova decisão o contradiz, o novo ADR
  marca o antigo como `Superseded by ADR-NNN` (o antigo não é reescrito, só o campo Status).
- Decisões pequenas e reversíveis não precisam de ADR — registre no doc do módulo.

## 2. Numerar

```bash
ls docs/adr/ | grep -E '^[0-9]{3}-' | sort | tail -1
```

Próximo número com 3 dígitos; arquivo `docs/adr/NNN-titulo-em-kebab-case.md` (título do arquivo em
inglês, conteúdo em português).

## 3. Escrever

Use `.claude/templates/adr.md`. Exigências:
- **Context**: problema concreto e forças; sem solução.
- **Decision**: primeira frase é a decisão.
- **Alternatives Considered**: pelo menos duas alternativas reais com prós/contras/por que não.
- **Consequences**: positivas, custos aceitos, riscos com mitigação e **gatilho para revisitar**.
- Status inicial `Proposed`, a menos que o usuário confirme `Accepted`.

## 4. Indexar

Adicione a linha no índice de `docs/adr/README.md` e referencie o ADR nos documentos de arquitetura
ou domínio afetados.
