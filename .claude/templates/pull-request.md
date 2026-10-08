## O que muda

<Resumo em 1–3 frases.>

## Por quê

<Problema que existia. Link para issue/ADR/doc de domínio.>

## Decisões e trade-offs

<Alternativas consideradas e o que aceitamos.>

## Como testar

- [ ] `moon run :check`
- [ ] <passos manuais, se houver>

## Checklist (Definition of Done)

- [ ] Regra no domínio + validação + autorização
- [ ] Testes (caminho feliz e erros) — concorrência/idempotência quando aplicável
- [ ] Erros no envelope padrão; logs estruturados sem dados sensíveis
- [ ] Migrations revisadas (`sqlmigrate`)
- [ ] OpenAPI atualizado
- [ ] Frontend: loading / empty / error states, acessibilidade, i18n
- [ ] Revisão de segurança e de arquitetura
- [ ] Docs de domínio / ADR atualizados
