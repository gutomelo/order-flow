---
name: review-security
description: Revisão de segurança das mudanças atuais do OrderFlow — autenticação JWT, autorização RBAC, IDOR, mass assignment, validação, exposição de dados, logs sensíveis, secrets, CORS e rate limiting. Use antes de abrir PR que toque API, auth, permissões, configuração ou dependências.
argument-hint: [escopo: módulo, caminho ou "diff"]
context: fork
agent: security-reviewer
---

# Revisão de segurança

Escopo: `$ARGUMENTS` (se vazio, revise o diff da branch atual contra `master` e as mudanças não
commitadas).

1. Leia `docs/architecture/security.md`, `docs/adr/007-jwt-authentication.md` e
   `.claude/rules/security.md`.
2. Colete o diff: `git diff master...HEAD`, `git diff`, `git diff --staged`.
3. Para cada arquivo alterado, leia o contexto completo (view + serializer + permission + queryset).
4. Aplique o checklist do agent (autenticação, autorização, IDOR, mass assignment, validação,
   exposição, logs, secrets, rate limiting, CORS/headers, dependências).
5. Procure ativamente:
   - `fields = "__all__"`, `get_object_or_404(Model, id=...)` sem queryset escopado;
   - `AllowAny`, ausência de `permission_classes`;
   - `logger.*(...)` com `token`, `password`, `authorization`, `card`;
   - `raw(`, `extra(`, `cursor.execute(` com interpolação;
   - valores que parecem secrets em arquivos versionados.
6. Relatório no formato de `.claude/templates/review-report.md`. Só achados com cenário de ataque
   concreto; caso contrário, "Sem achados".
