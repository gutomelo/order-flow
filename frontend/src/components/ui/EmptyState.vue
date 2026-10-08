<script setup lang="ts">
import type { Component } from 'vue'

/** Estado vazio: sempre explica o motivo e o próximo passo (nunca apenas "Nenhum dado"). */
defineProps<{ title: string; description: string; icon?: Component }>()
</script>

<template>
  <div
    class="flex flex-col items-center rounded-lg border border-dashed border-border bg-surface px-6 py-12 text-center"
  >
    <span
      v-if="icon"
      class="mb-4 flex size-10 items-center justify-center rounded-full bg-surface-muted text-text-secondary"
    >
      <component :is="icon" class="size-5" aria-hidden="true" />
    </span>
    <h2 class="text-base font-semibold text-text-primary">{{ title }}</h2>
    <p class="mt-1 max-w-md text-sm text-text-secondary">{{ description }}</p>
    <div v-if="$slots.action" class="mt-4">
      <slot name="action" />
    </div>
  </div>
</template>
