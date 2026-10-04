import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  tone: 'success' | 'error'
  message: string
}

const DISMISS_AFTER_MS = 5_000

/** Feedback de sucesso/erro de operações (client state). */
export const useToastStore = defineStore('toasts', () => {
  const toasts = ref<Toast[]>([])
  let nextId = 1

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((toast) => toast.id !== id)
  }

  function push(tone: Toast['tone'], message: string) {
    const id = nextId++
    toasts.value.push({ id, tone, message })
    setTimeout(() => dismiss(id), DISMISS_AFTER_MS)
  }

  return {
    toasts,
    dismiss,
    success: (message: string) => push('success', message),
    error: (message: string) => push('error', message),
  }
})
