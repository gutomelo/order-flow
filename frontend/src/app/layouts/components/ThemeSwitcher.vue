<script setup lang="ts">
import { Monitor, Moon, Sun } from '@lucide/vue'
import type { Component } from 'vue'
import { useI18n } from 'vue-i18n'

import { type ThemePreference, useUiStore } from '@/app/stores/ui'

const { t } = useI18n()
const ui = useUiStore()

const options: { value: ThemePreference; labelKey: string; icon: Component }[] = [
  { value: 'light', labelKey: 'theme.light', icon: Sun },
  { value: 'dark', labelKey: 'theme.dark', icon: Moon },
  { value: 'system', labelKey: 'theme.system', icon: Monitor },
]
</script>

<template>
  <div
    role="group"
    :aria-label="t('theme.label')"
    class="inline-flex items-center rounded-md border border-border bg-surface p-0.5"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="inline-flex size-7 items-center justify-center rounded text-text-secondary hover:text-text-primary aria-pressed:bg-surface-muted aria-pressed:text-text-primary"
      :aria-pressed="ui.theme === option.value"
      :title="t(option.labelKey)"
      @click="ui.setTheme(option.value)"
    >
      <component :is="option.icon" class="size-4" aria-hidden="true" />
      <span class="sr-only">{{ t(option.labelKey) }}</span>
    </button>
  </div>
</template>
