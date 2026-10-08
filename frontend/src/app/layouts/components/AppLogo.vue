<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { inverted = false } = defineProps<{ inverted?: boolean }>()

const { t } = useI18n()
</script>

<template>
  <span class="flex items-center gap-2">
    <span
      class="flex size-7 items-center justify-center rounded-md bg-primary text-xs font-semibold text-on-primary"
      aria-hidden="true"
    >
      OF
    </span>
    <span
      class="text-sm font-semibold tracking-tight"
      :class="inverted ? 'text-sidebar-text-active' : 'text-text-primary'"
    >
      {{ t('app.name') }}
    </span>
  </span>
</template>
