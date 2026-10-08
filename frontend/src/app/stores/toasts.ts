import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast {
  id: number
  tone: 'success' | 'warning' | 'error'
  message: string
}

const DISMISS_AFTER_MS = 5_000

/** Feedback de operações (client state). `warning`: concluiu, mas com ressalva. */
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
    warning: (message: string) => push('warning', message),
    error: (message: string) => push('error', message),
  }
})
