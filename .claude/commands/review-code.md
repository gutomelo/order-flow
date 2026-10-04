---
description: Revisão completa das mudanças atuais — código, domínio, segurança, arquitetura e (se houver frontend) UX — consolidada em um único relatório.
argument-hint: [escopo opcional: caminho, módulo ou branch base]
disable-model-invocation: true
---

# Revisão de código: $ARGUMENTS

## Contexto

- Arquivos alterados vs master: !`git diff master...HEAD --name-only 2>/dev/null`
- Não commitados: !`git status --short`

## Instruções

1. Delegue em paralelo aos agents somente-leitura, passando o escopo acima:
   - `code-reviewer` (sempre);
   - `domain-reviewer` (se houver mudanças em `backend/apps/*/domain`, `application`, `models`);
   - `security-reviewer` (se houver mudanças em `api/`, auth, settings, dependências, logs);
   - `software-architect` em modo revisão (se houver novos módulos, novas abstrações ou imports
     entre módulos);
   - `ux-reviewer` (se houver mudanças em `frontend/src`).
2. Consolide os resultados em um único relatório no formato de `.claude/templates/review-report.md`,
   removendo duplicatas e ordenando por severidade.
3. Termine com o veredito e a lista de ações obrigatórias antes do merge. Não aplique correções sem
   o usuário pedir.
