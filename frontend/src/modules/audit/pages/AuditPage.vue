<script setup lang="ts">
import { ScrollText } from '@lucide/vue'
import { computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { AUDIT_PAGE_SIZE } from '@/modules/audit/api/auditApi'
import AuditChanges from '@/modules/audit/components/AuditChanges.vue'
import { useAuditLogs } from '@/modules/audit/composables/useAuditLogs'
import {
  AUDIT_ACTIONS,
  ENTITY_TYPES,
  type AuditAction,
  type AuditFilters,
  type EntityType,
} from '@/modules/audit/types'
import { formatDateTime } from '@/utils/datetime'

const { t } = useI18n()
const errorMessage = useApiErrorMessage()
const fromId = useId()
const toId = useId()

const isDay = (raw: string) => (/^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : undefined)
const { filters, field, hasActiveFilters } = useUrlFilters<AuditFilters>(
  { page: 1, search: '', action: '', entity_type: '', from: '', to: '' },
  {
    action: (raw) =>
      AUDIT_ACTIONS.includes(raw as AuditAction) ? (raw as AuditAction) : undefined,
    entity_type: (raw) =>
      ENTITY_TYPES.includes(raw as EntityType) ? (raw as EntityType) : undefined,
    from: isDay,
    to: isDay,
  },
)
const search = field('search')
const action = field('action')
const entityType = field('entity_type')
const from = field('from')
const to = field('to')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useAuditLogs(filters)

const actionOptions = computed(() => [
  { value: '', label: t('audit.filters.allActions') },
  ...AUDIT_ACTIONS.map((value) => ({ value, label: t(`audit.actions.${value}`) })),
])
const entityOptions = computed(() => [
  { value: '', label: t('audit.filters.allEntities') },
  ...ENTITY_TYPES.map((value) => ({ value, label: t(`audit.entities.${value}`) })),
])
const columns = computed(() => [
  { key: 'occurred_at', label: t('audit.fields.when') },
  { key: 'actor', label: t('audit.fields.actor') },
  { key: 'action', label: t('audit.fields.action') },
  { key: 'entity', label: t('audit.fields.entity') },
  { key: 'changes', label: t('audit.fields.details') },
])
</script>

<template>
  <div>
    <PageHeader :title="t('audit.title')" :description="t('audit.description')" />

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('audit.filters.search')" />
      <SelectField
        v-model="action"
        :label="t('audit.fields.action')"
        :options="actionOptions"
        hide-label
      />
      <SelectField
        v-model="entityType"
        :label="t('audit.fields.entity')"
        :options="entityOptions"
        hide-label
      />
      <div class="flex flex-col gap-1.5">
        <label :for="fromId" class="text-xs text-text-secondary">{{
          t('audit.filters.from')
        }}</label>
        <input
          :id="fromId"
          v-model.lazy="from"
          type="date"
          class="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary"
        />
      </div>
      <div class="flex flex-col gap-1.5">
        <label :for="toId" class="text-xs text-text-secondary">{{ t('audit.filters.to') }}</label>
        <input
          :id="toId"
          v-model.lazy="to"
          type="date"
          class="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary"
        />
      </div>
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('audit.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="AUDIT_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('audit.error.title')"
      :empty-title="t('audit.empty.title')"
      :empty-description="t('audit.empty.description')"
      :empty-icon="ScrollText"
      :filtered="hasActiveFilters"
      @retry="refetch()"
    >
      <template #cell-occurred_at="{ row }">
        <span class="text-text-secondary tabular-nums">{{ formatDateTime(row.occurred_at) }}</span>
      </template>
      <template #cell-actor="{ row }">
        <span v-if="row.actor">{{ row.actor.name }}</span>
        <span v-else class="text-text-secondary">{{ t('audit.system') }}</span>
      </template>
      <template #cell-action="{ row }">{{ t(`audit.actions.${row.action}`) }}</template>
      <template #cell-entity="{ row }">
        <p class="text-xs text-text-secondary">{{ t(`audit.entities.${row.entity_type}`) }}</p>
        <RouterLink
          v-if="row.order_id"
          :to="{ name: 'order-detail', params: { id: row.order_id } }"
          class="font-medium text-link tabular-nums underline-offset-2 hover:underline"
        >
          {{ row.entity_label }}
        </RouterLink>
        <span v-else class="font-medium">{{ row.entity_label }}</span>
      </template>
      <template #cell-changes="{ row }">
        <AuditChanges :log="row" />
      </template>
    </DataTable>
  </div>
</template>
