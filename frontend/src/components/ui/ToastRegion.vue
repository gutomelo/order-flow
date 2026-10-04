<script setup lang="ts">
import { CircleAlert, CircleCheck, X } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'

const { t } = useI18n()
const toasts = useToastStore()
</script>

<template>
  <!-- Região viva: leitores de tela anunciam o feedback sem mover o foco. -->
  <div
    class="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[calc(100%-2rem)] max-w-sm flex-col gap-2"
    role="status"
    aria-live="polite"
  >
    <div
      v-for="toast in toasts.toasts"
      :key="toast.id"
      class="pointer-events-auto flex items-start gap-3 rounded-lg border border-border bg-surface p-3 text-sm text-text-primary shadow-lg"
    >
      <component
        :is="toast.tone === 'success' ? CircleCheck : CircleAlert"
        class="mt-0.5 size-4 shrink-0"
        :class="toast.tone === 'success' ? 'text-success' : 'text-danger'"
        aria-hidden="true"
      />
      <p class="flex-1">{{ toast.message }}</p>
      <button
        type="button"
        class="-m-1 inline-flex size-6 items-center justify-center rounded text-text-secondary hover:text-text-primary"
        :aria-label="t('common.close')"
        @click="toasts.dismiss(toast.id)"
      >
        <X class="size-3.5" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
