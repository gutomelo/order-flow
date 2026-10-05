import { nextTick, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { z } from 'zod'

import { ApiError } from '@/services/http/apiError'

type FieldErrors<T> = Partial<Record<keyof T & string, string>>

/**
 * Estado de formulário validado por um schema Zod.
 *
 * - Validação client-side = feedback antecipado; o backend continua sendo a autoridade.
 * - Erros de validação do backend (`VALIDATION_ERROR.details.fields`) são mapeados para os campos.
 * - `submit` impede envio duplo enquanto a requisição está em andamento.
 * - Com erro de campo (local ou do servidor), o foco vai para o primeiro campo inválido.
 */
export function useZodForm<Schema extends z.ZodObject>(
  schema: Schema,
  initialValues: z.input<Schema>,
) {
  type Values = z.input<Schema>
  const { t, te } = useI18n()

  const values = reactive({ ...initialValues }) as Values
  const errors = ref<FieldErrors<Values>>({})
  const formError = ref<string | null>(null)
  const isSubmitting = ref(false)

  const translate = (message: string) => (te(message) ? t(message) : message)

  function validate(): z.output<Schema> | null {
    const result = schema.safeParse(values)
    if (result.success) {
      errors.value = {}
      return result.data
    }
    const next: Record<string, string> = {}
    for (const issue of result.error.issues) {
      const field = String(issue.path[0] ?? '')
      next[field] ??= translate(issue.message)
    }
    errors.value = next as FieldErrors<Values>
    return null
  }

  function applyServerError(error: unknown): boolean {
    if (!(error instanceof ApiError)) return false
    // Erro de domínio ligado a um campo (ex.: INVALID_BARCODE com details.field = "barcode"):
    // a mensagem aparece no próprio campo, não no topo do formulário.
    const field = error.details.field
    if (typeof field === 'string' && field in values) {
      errors.value = { [field]: error.message } as FieldErrors<Values>
      return true
    }
    if (error.code !== 'VALIDATION_ERROR') return false
    const fields = (error.details.fields ?? {}) as Record<string, string[] | string>
    const next: Record<string, string> = {}
    for (const [field, messages] of Object.entries(fields)) {
      next[field] = Array.isArray(messages) ? (messages[0] ?? '') : messages
    }
    errors.value = next as FieldErrors<Values>
    return true
  }

  /**
   * Foco no primeiro campo com `aria-invalid` do formulário que foi enviado. O botão de envio pode
   * ficar fora do `<form>` (rodapé do diálogo, `form="..."`): `.form` resolve os dois casos.
   */
  async function focusFirstInvalid(origin: Element | null) {
    await nextTick()
    const form =
      origin instanceof HTMLButtonElement || origin instanceof HTMLInputElement
        ? origin.form
        : origin?.closest('form')
    ;(form ?? document).querySelector<HTMLElement>('[aria-invalid="true"]')?.focus()
  }

  /**
   * Valida e executa `action`. Erros de validação do servidor vão para os campos; os demais
   * são repassados ao `onError` (ex.: mensagem geral do formulário).
   */
  async function submit(
    action: (data: z.output<Schema>) => Promise<unknown>,
    onError?: (error: unknown) => unknown,
  ): Promise<boolean> {
    if (isSubmitting.value) return false
    const origin = document.activeElement
    formError.value = null
    const data = validate()
    if (!data) {
      await focusFirstInvalid(origin)
      return false
    }
    isSubmitting.value = true
    let fieldError = false
    try {
      await action(data)
      return true
    } catch (error) {
      fieldError = applyServerError(error)
      if (!fieldError) await onError?.(error)
      return false
    } finally {
      isSubmitting.value = false
      if (fieldError) await focusFirstInvalid(origin)
    }
  }

  function reset(next: Values = initialValues) {
    Object.assign(values, next)
    errors.value = {}
    formError.value = null
  }

  return { values, errors, formError, isSubmitting, validate, submit, reset }
}
