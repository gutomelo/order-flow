<script setup lang="ts">
import { LoaderCircle } from '@lucide/vue'

const {
  variant = 'primary',
  size = 'md',
  type = 'button',
  loading = false,
  disabled = false,
} = defineProps<{
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
  type?: 'button' | 'submit'
  loading?: boolean
  disabled?: boolean
}>()

const variants = {
  primary: 'bg-primary text-on-primary hover:bg-primary-hover',
  secondary: 'border border-border bg-surface text-text-primary hover:bg-surface-muted',
  danger: 'bg-danger text-on-primary hover:opacity-90',
  ghost: 'text-text-secondary hover:bg-surface-muted hover:text-text-primary',
}
const sizes = { sm: 'h-8 px-3 text-sm', md: 'h-9 px-4 text-sm' }
</script>

<template>
  <!-- Desabilitado durante o envio: evita double-submit. -->
  <button
    :type="type"
    :disabled="disabled || loading"
    :aria-busy="loading"
    class="inline-flex shrink-0 items-center justify-center gap-2 rounded-md font-medium whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-60"
    :class="[variants[variant], sizes[size]]"
  >
    <LoaderCircle v-if="loading" class="size-4 animate-spin" aria-hidden="true" />
    <slot />
  </button>
</template>
