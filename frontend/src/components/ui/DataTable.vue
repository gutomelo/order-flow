<script setup lang="ts" generic="Row extends { id: string }">
import { CircleSlash } from '@lucide/vue'
import type { Component } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import TablePagination from '@/components/ui/TablePagination.vue'

export interface DataTableColumn {
  key: string
  label: string
  /** Cabeçalho apenas para leitores de tela (ex.: coluna de ações). */
  srOnly?: boolean
  align?: 'left' | 'right'
}

/**
 * Tabela de listagem com todos os estados obrigatórios (frontend.md): loading com skeleton,
 * erro com "tentar novamente", vazio (diferenciando "sem dados" de "sem resultado para os filtros")
 * e paginação. Células customizadas via slot `cell-<key>`.
 */
const page = defineModel<number>('page', { default: 1 })
const {
  caption,
  columns,
  rows,
  count = 0,
  pageSize = 25,
  paginated = true,
  pending = false,
  fetching = false,
  error = null,
  errorTitle,
  emptyTitle,
  emptyDescription,
  emptyIcon,
  filtered = false,
  filteredTitle,
  filteredDescription,
  minWidth = '720px',
} = defineProps<{
  caption: string
  columns: DataTableColumn[]
  rows: Row[] | undefined
  count?: number
  pageSize?: number
  paginated?: boolean
  pending?: boolean
  fetching?: boolean
  error?: string | null
  errorTitle: string
  emptyTitle: string
  emptyDescription: string
  emptyIcon: Component
  filtered?: boolean
  filteredTitle?: string
  filteredDescription?: string
  minWidth?: string
}>()
const emit = defineEmits<{ retry: [] }>()

const { t } = useI18n()

function cellValue(row: Row, key: string): string {
  const value = (row as unknown as Record<string, unknown>)[key]
  return value === null || value === undefined || value === '' ? '—' : String(value)
}
</script>

<template>
  <div
    v-if="pending"
    class="space-y-2 rounded-lg border border-border bg-surface p-4"
    role="status"
  >
    <span class="sr-only">{{ t('common.loading') }}</span>
    <div v-for="index in 5" :key="index" class="h-9 animate-pulse rounded bg-surface-muted" />
  </div>

  <EmptyState
    v-else-if="error !== null"
    :title="errorTitle"
    :description="error"
    :icon="CircleSlash"
    role="alert"
  >
    <template #action>
      <BaseButton variant="secondary" :loading="fetching" @click="emit('retry')">
        {{ t('common.retry') }}
      </BaseButton>
    </template>
  </EmptyState>

  <EmptyState
    v-else-if="rows && rows.length === 0"
    :title="filtered ? (filteredTitle ?? t('common.noResultsTitle')) : emptyTitle"
    :description="
      filtered ? (filteredDescription ?? t('common.noResultsDescription')) : emptyDescription
    "
    :icon="emptyIcon"
  >
    <template v-if="!filtered && $slots['empty-action']" #action>
      <slot name="empty-action" />
    </template>
  </EmptyState>

  <div v-else-if="rows" class="rounded-lg border border-border bg-surface">
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm" :style="{ minWidth }" :aria-busy="fetching">
        <caption class="sr-only">
          {{
            caption
          }}
        </caption>
        <thead class="border-b border-border text-xs font-medium text-text-secondary">
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              class="px-4 py-3"
              :class="{ 'text-right': column.align === 'right' }"
            >
              <span :class="{ 'sr-only': column.srOnly }">{{ column.label }}</span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border">
          <tr v-for="row in rows" :key="row.id" class="hover:bg-surface-muted/50">
            <td
              v-for="column in columns"
              :key="column.key"
              class="px-4 py-3 text-text-primary"
              :class="{ 'text-right': column.align === 'right' }"
            >
              <slot :name="`cell-${column.key}`" :row="row">
                {{ cellValue(row, column.key) }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="paginated" class="border-t border-border px-4 py-3">
      <TablePagination v-model:page="page" :count="count" :page-size="pageSize" />
    </div>
  </div>
</template>
