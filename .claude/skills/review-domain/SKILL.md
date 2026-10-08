---
name: review-domain
description: Revisa regras de negócio das mudanças atuais do OrderFlow contra a documentação de domínio — invariantes, transições de estado, regras duplicadas, domínio anêmico, lógica em camadas inadequadas e linguagem ubíqua. Use após alterar pedidos, estoque, preços, pagamentos ou envio.
argument-hint: [módulo ou "diff"]
context: fork
agent: domain-reviewer
---

# Revisão de domínio

Escopo: `$ARGUMENTS` (se vazio, revise o diff da branch atual contra `master`).

1. Identifique os módulos afetados e leia `docs/domain/<module>.md`, `docs/domain/glossary.md` e os
   ADRs relacionados (ex.: ADR-008 para estoque).
2. Leia o diff e o código de domínio/application dos módulos afetados.
3. Compare implementação × especificação:
   - invariantes do doc estão no domínio e, quando críticas, no banco;
   - tabela de transições implementada exatamente (permitidas e proibidas);
   - `OrderStatusHistory` / `StockMovement` / auditoria gerados onde exigido;
   - nenhuma regra em view, serializer, permission, signal, task ou componente Vue;
   - nenhuma regra duplicada entre camadas/módulos;
   - nomes seguem o glossário.
4. Divergência entre doc e código é achado: diga qual dos dois deve mudar e por quê.
5. Relatório no formato de `.claude/templates/review-report.md`.
