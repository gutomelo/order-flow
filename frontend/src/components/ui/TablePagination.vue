<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const page = defineModel<number>('page', { required: true })
const { count, pageSize } = defineProps<{ count: number; pageSize: number }>()

const { t } = useI18n()
const totalPages = computed(() => Math.max(1, Math.ceil(count / pageSize)))
const first = computed(() => (count === 0 ? 0 : (page.value - 1) * pageSize + 1))
const last = computed(() => Math.min(page.value * pageSize, count))
</script>

<template>
  <nav
    class="flex flex-wrap items-center justify-between gap-3 text-sm text-text-secondary"
    :aria-label="t('pagination.label')"
  >
    <p class="tabular-nums">{{ t('pagination.range', { first, last, count }) }}</p>
    <div class="flex items-center gap-1">
      <button
        type="button"
        class="inline-flex size-8 items-center justify-center rounded-md border border-border bg-surface text-text-primary hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="page <= 1"
        :aria-label="t('pagination.previous')"
        @click="page -= 1"
      >
        <ChevronLeft class="size-4" aria-hidden="true" />
      </button>
      <span class="px-2 tabular-nums">{{ t('pagination.page', { page, total: totalPages }) }}</span>
      <button
        type="button"
        class="inline-flex size-8 items-center justify-center rounded-md border border-border bg-surface text-text-primary hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="page >= totalPages"
        :aria-label="t('pagination.next')"
        @click="page += 1"
      >
        <ChevronRight class="size-4" aria-hidden="true" />
      </button>
    </div>
  </nav>
</template>
