# Padrões de código

## Idioma

| O quê | Idioma |
| --- | --- |
| Código (classes, funções, variáveis, tabelas, campos, eventos, endpoints, arquivos) | **inglês** |
| Códigos de erro da API | inglês (`INSUFFICIENT_STOCK`) |
| Mensagens de erro para o usuário | pt-BR |
| Comentários | português ou inglês — explicar o porquê |
| Documentação interna | português |
| UI | pt-BR via i18n |

Termos de negócio: [../domain/glossary.md](../domain/glossary.md).

## Princípios

- **Clean Code pragmático**: nomes que revelam intenção, funções pequenas com um nível de abstração,
  sem efeitos colaterais escondidos, sem comentários que repetem o código.
- **SOLID pragmático**: SRP sempre; OCP/Strategy onde há variação real; ISP com `Protocol`s pequenos;
  DIP para dependências externas relevantes; LSP — implementações de uma porta (`FakePaymentGateway`,
  `StripePaymentGateway`) respeitam o mesmo contrato e passam na mesma suíte de testes de contrato.
- **Anti-overengineering**: nenhuma abstração sem problema concreto ("qual problema isto resolve
  agora?"). Três usos parecidos antes de extrair uma abstração.
- **Sem god classes**: um use case por intenção de negócio.

## Python

| Tema | Padrão |
| --- | --- |
| Formatação | `ruff format` (sem Black — Ruff cobre o mesmo estilo; duas ferramentas seriam redundantes) |
| Lint | `ruff check` com regras: `E`, `F`, `W`, `I` (imports), `B` (bugbear), `UP` (pyupgrade), `DJ` (Django), `S` (bandit), `SIM`, `RUF`, `PL` seletivo, `DTZ` (datas sem timezone), `T20` (sem `print`) |
| Tipos | type hints em funções públicas; mypy com plugins Django/DRF; `strict` por módulo novo quando viável |
| Linha | 100 caracteres |
| Imports | absolutos (`from apps.orders.domain.events import OrderCreated`); ordenados pelo Ruff |
| Nomes | `snake_case` funções/variáveis, `PascalCase` classes, `SCREAMING_SNAKE_CASE` constantes/enums |
| Use cases | classe com verbo no imperativo (`CancelOrder`) + `execute(command)`; command `@dataclass(frozen=True)` |
| Exceções | herdar de `DomainError` com `code` estável; nunca `except Exception: pass` |
| Dinheiro | `Decimal` / `Money`; proibido `float` (regra de lint/revisão) |
| Datas | `timezone.now()`; proibido `datetime.now()`/`utcnow()` (regra `DTZ`) |
| Logs | `structlog`, evento `module.entity.action`, contexto em chaves |

### Django

- Models: `class Meta` com `constraints`, `indexes`, `ordering` quando relevante; `__str__` útil.
- Sem lógica de negócio em `save()` ou signals; ela vive no domínio/use case.
- `select_related`/`prefetch_related` nas listagens.
- Admin apenas para operação/inspeção; ações que alteram estado de negócio passam pelos use cases.

## TypeScript / Vue

| Tema | Padrão |
| --- | --- |
| Formatação | Prettier (sem ponto e vírgula, aspas simples, 100 colunas) |
| Lint | ESLint flat config com `eslint-plugin-vue` (recommended), `typescript-eslint` (strict), compatível com Prettier |
| Tipos | `strict: true`, `noUncheckedIndexedAccess: true`; proibido `any` |
| Componentes | `<script setup lang="ts">`, `PascalCase.vue`, props/emits tipados (`defineProps<T>()`) |
| Composables | `useXxx.ts`, retornam refs/computed tipados |
| Arquivos | `camelCase.ts` para módulos, `PascalCase.vue` para componentes, páginas com sufixo `Page` |
| i18n | chaves em inglês por feature: `orders.actions.cancel` |
| Estilo | apenas tokens CSS semânticos; sem hex em componentes |

## Pre-commit

Hooks locais (rápidos): `ruff check --fix`, `ruff format`, `prettier`, verificação de arquivos
grandes, de chaves privadas e de merge conflicts. Verificações pesadas (mypy, testes) ficam no
`moon run :check` e na CI.

## Revisão

Toda mudança relevante passa por `/review-code` (code-reviewer + reviewers especializados conforme o
diff). Checklist de PR em `.claude/templates/pull-request.md`.
