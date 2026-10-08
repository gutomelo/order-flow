<script setup lang="ts">
import type { Component } from 'vue'

/** Status nunca depende só de cor: sempre ícone + texto + cor (WCAG 1.4.1). */
const {
  label,
  icon,
  tone = 'neutral',
} = defineProps<{
  label: string
  icon: Component
  tone?: 'success' | 'danger' | 'warning' | 'info' | 'neutral'
}>()

const tones = {
  success: 'text-success',
  danger: 'text-danger',
  warning: 'text-warning',
  info: 'text-info',
  neutral: 'text-text-secondary',
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2 py-0.5 text-xs font-medium text-text-primary"
  >
    <component :is="icon" class="size-3.5" :class="tones[tone]" aria-hidden="true" />
    {{ label }}
  </span>
</template>
