---
description: Mostra o estado atual do OrderFlow — fase do roadmap, módulos existentes, mudanças pendentes, saúde das tarefas Moon e próximos passos.
disable-model-invocation: true
---

# Status do projeto

## Contexto coletado

- Branch e mudanças: !`git status --short --branch`
- Últimos commits: !`git log --oneline -10`
- Módulos backend existentes: !`ls backend/apps 2>/dev/null || echo "(backend ainda não criado)"`
- Features frontend existentes: !`ls frontend/src/modules 2>/dev/null || echo "(frontend ainda não criado)"`
- ADRs: !`ls docs/adr 2>/dev/null`

## Instruções

1. Leia a seção **Roadmap** de `docs/architecture/overview.md` e determine em que fase o projeto
   está, comparando com os módulos/features existentes e com a linha "Fase atual" do `CLAUDE.md`.
2. Se `moon` estiver instalado e os projetos existirem, rode `moon query projects` e, se o usuário
   não se opuser a esperar, `moon run :check` — reporte falhas resumidas.
3. Responda em português, curto:
   - **Fase atual** e o que falta para concluí-la (critérios da fase no roadmap);
   - **Mudanças não commitadas** relevantes;
   - **Saúde**: resultado do check (ou "não executado");
   - **Divergências**: docs desatualizados em relação ao código, se notar;
   - **Próximos 3 passos** recomendados.
