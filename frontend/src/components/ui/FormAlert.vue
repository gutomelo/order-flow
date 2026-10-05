<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'

/** Erro geral do formulário (sem campo associado), anunciado por leitores de tela. */
defineProps<{ message: string | null | undefined }>()
</script>

<template>
  <div
    v-if="message"
    class="flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm"
    role="alert"
  >
    <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
    {{ message }}
  </div>
</template>
