import { ref } from 'vue'

import { useToastStore } from '@/app/stores/toasts'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'

interface Activatable {
  id: string
  is_active: boolean
}

/**
 * Fluxo "ativar/inativar com confirmação" (inativação no lugar de exclusão):
 * `ask(row)` abre o diálogo; `confirm()` executa, mostra feedback e fecha.
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

  function ask(row: Row) {
    target.value = row
    open.value = true
  }

  async function confirm() {
    const row = target.value
    if (!row || running.value) return
    running.value = true
    try {
      await options.mutate({ id: row.id, active: !row.is_active })
      toasts.success(options.successMessage(row))
      open.value = false
    } catch (error) {
      toasts.error(errorMessage(error))
    } finally {
      running.value = false
    }
  }

  return { target, open, running, ask, confirm }
}
