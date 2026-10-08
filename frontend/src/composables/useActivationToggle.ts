import { ref } from 'vue'

import { useToastStore } from '@/app/stores/toasts'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'

interface Activatable {
  id: string
  is_active: boolean
}

/**
 * Fluxo "ativar/inativar com confirmação" (inativação no lugar de exclusão):
 * `ask(row)` abre o diálogo; `confirm()` executa e, no sucesso, fecha com um toast. A falha
 * fica em `error`, exibida dentro do diálogo (ver `ConfirmDialog`).
 */
export function useActivationToggle<Row extends Activatable>(options: {
  mutate: (input: { id: string; active: boolean }) => Promise<unknown>
  successMessage: (row: Row) => string
}) {
  const toasts = useToastStore()
  const errorMessage = useApiErrorMessage()

  const target = ref<Row | null>(null)
  const open = ref(false)
  const running = ref(false)
  const error = ref<string | null>(null)

  function ask(row: Row) {
    target.value = row
    error.value = null
    open.value = true
  }

  async function confirm() {
    const row = target.value
    if (!row || running.value) return
    running.value = true
    error.value = null
    try {
      await options.mutate({ id: row.id, active: !row.is_active })
      toasts.success(options.successMessage(row))
      open.value = false
    } catch (cause) {
      error.value = errorMessage(cause)
    } finally {
      running.value = false
    }
  }

  return { target, open, running, error, ask, confirm }
}
