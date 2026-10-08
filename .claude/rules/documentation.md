---
paths:
  - "docs/**"
  - "CLAUDE.md"
  - "README.md"
---

# Documentação

- Documentação interna em português; termos técnicos consagrados em inglês (commit, deploy, lock).
- Identificadores de código citados exatamente como no código (inglês, em `code`).
- ADRs: `docs/adr/NNN-kebab-case.md`, formato Status / Context / Decision / Alternatives
  Considered / Consequences (template em `.claude/templates/adr.md`). ADR aceito não é reescrito:
  é substituído por outro ADR (`Superseded by ADR-XXX`).
- Diagramas em Mermaid dentro do Markdown (renderiza no GitHub). C4: Context, Container,
  Component (`docs/diagrams/c4-model.md`).
- Cada documento responde: qual problema, qual decisão, quais alternativas, quais trade-offs.
- Documento de domínio (`docs/domain/<module>.md`) é a fonte das regras de negócio: atualize-o no
  mesmo PR que muda a regra.
- Atualize o índice (`docs/adr/README.md`, `docs/domain/README.md`) ao criar documentos.
