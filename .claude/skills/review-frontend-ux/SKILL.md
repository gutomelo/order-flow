---
name: review-frontend-ux
description: Revisa UX, acessibilidade e consistência visual das telas/componentes Vue alterados no OrderFlow — loading/success/error, empty states, formulários, confirmações, tabelas, status badges, WCAG, responsividade e uso de design tokens. Use após criar ou alterar páginas e componentes.
argument-hint: [feature, caminho ou "diff"]
context: fork
agent: ux-reviewer
---

# Revisão de UX do frontend

Escopo: `$ARGUMENTS` (se vazio, os arquivos `frontend/` alterados na branch atual contra `master`).

1. Leia `docs/architecture/frontend.md` (design system, layout, tokens) e `.claude/rules/frontend-ui.md`.
2. Liste os arquivos: `git diff master...HEAD --name-only -- frontend/` (+ mudanças não commitadas).
3. Para cada página/componente, verifique o checklist do agent: feedback, ações destrutivas, empty
   states, formulários, tabelas, status, acessibilidade, responsividade, consistência.
4. Procure ativamente:
   - cores hexadecimais/rgb fora de `tokens.css`;
   - texto literal em template (deveria ser i18n);
   - `useQuery` sem tratamento de `isError`/estado vazio;
   - botões só-ícone sem `aria-label`; `div` clicável sem semântica de botão;
   - `useMutation` cujo botão não desabilita durante `isPending`.
5. Se o app estiver rodando e houver ferramenta de navegador disponível, valide visualmente
   (incluindo largura mobile) — opcional.
6. Relatório no formato de `.claude/templates/review-report.md`, ordenado por impacto no usuário.
