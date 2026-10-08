<script setup lang="ts">
import { History, X } from '@lucide/vue'
import { computed, useId } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { MOVEMENTS_PAGE_SIZE } from '@/modules/inventory/api/inventoryApi'
import MovementTypeBadge from '@/modules/inventory/components/MovementTypeBadge.vue'
import { useMovementList, useWarehouses } from '@/modules/inventory/composables/useInventory'
import { MOVEMENT_TYPES, type MovementFilters, type MovementType } from '@/modules/inventory/types'
import { formatDateTime } from '@/utils/datetime'

const { t } = useI18n()
const errorMessage = useApiErrorMessage()
const fromId = useId()
const toId = useId()

const isDay = (raw: string) => (/^\d{4}-\d{2}-\d{2}$/.test(raw) ? raw : undefined)
const { filters, field, update, hasActiveFilters } = useUrlFilters<MovementFilters>(
  { page: 1, search: '', type: '', warehouse: '', product: '', from: '', to: '' },
  {
    type: (raw) =>
      MOVEMENT_TYPES.includes(raw as MovementType) ? (raw as MovementType) : undefined,
    from: isDay,
    to: isDay,
  },
)
const search = field('search')
const type = field('type')
const warehouse = field('warehouse')
const from = field('from')
const to = field('to')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useMovementList(filters)
const warehouses = useWarehouses()

const typeOptions = computed(() => [
  { value: '', label: t('inventory.filters.allTypes') },
  ...MOVEMENT_TYPES.map((value) => ({ value, label: t(`inventory.movementTypes.${value}`) })),
])
const warehouseOptions = computed(() => [
  { value: '', label: t('inventory.filters.allWarehouses') },
  ...(warehouses.data.value ?? []).map((w) => ({ value: w.id, label: `${w.code} — ${w.name}` })),
])
const columns = computed(() => [
  { key: 'created_at', label: t('inventory.fields.when') },
  { key: 'type', label: t('inventory.fields.type') },
  { key: 'product', label: t('inventory.fields.product') },
  { key: 'warehouse', label: t('inventory.fields.warehouse') },
  { key: 'delta', label: t('inventory.fields.delta'), align: 'right' as const },
  { key: 'after', label: t('inventory.fields.balanceAfter'), align: 'right' as const },
  { key: 'details', label: t('inventory.fields.details') },
])

const signed = (value: number) => (value > 0 ? `+${value}` : String(value))
</script>

<template>
  <div>
    <PageHeader
      :title="t('inventory.movements.title')"
      :description="t('inventory.movements.description')"
    />

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('inventory.filters.searchMovements')" />
      <SelectField
        v-model="type"
        :label="t('inventory.fields.type')"
        :options="typeOptions"
        hide-label
      />
      <SelectField
        v-model="warehouse"
        :label="t('inventory.fields.warehouse')"
        :options="warehouseOptions"
        hide-label
      />
      <div class="flex flex-col gap-1.5">
        <label :for="fromId" class="text-xs text-text-secondary">{{
          t('inventory.filters.from')
        }}</label>
        <input
          :id="fromId"
          v-model.lazy="from"
          type="date"
          class="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary"
        />
      </div>
      <div class="flex flex-col gap-1.5">
        <label :for="toId" class="text-xs text-text-secondary">{{
          t('inventory.filters.to')
        }}</label>
        <input
          :id="toId"
          v-model.lazy="to"
          type="date"
          class="h-9 rounded-md border border-border bg-surface px-3 text-sm text-text-primary"
        />
      </div>
      <BaseButton
        v-if="filters.product"
        variant="secondary"
        size="sm"
        @click="update({ product: '' })"
      >
        <X class="size-4" aria-hidden="true" />
        {{ t('inventory.filters.clearProduct') }}
      </BaseButton>
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('inventory.movements.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="MOVEMENTS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('inventory.movements.errorTitle')"
      :empty-title="t('inventory.movements.emptyTitle')"
      :empty-description="t('inventory.movements.emptyDescription')"
      :empty-icon="History"
      :filtered="hasActiveFilters"
      min-width="960px"
      @retry="refetch()"
    >
      <template #cell-created_at="{ row }">
        <span class="text-text-secondary tabular-nums">{{ formatDateTime(row.created_at) }}</span>
      </template>
      <template #cell-type="{ row }"><MovementTypeBadge :type="row.type" /></template>
      <template #cell-product="{ row }">
        <p class="font-medium">{{ row.product.name }}</p>
        <p class="font-mono text-xs text-text-secondary">{{ row.product.sku }}</p>
      </template>
      <template #cell-warehouse="{ row }">
        <span class="font-mono text-xs">{{ row.warehouse.code }}</span>
      </template>
      <template #cell-delta="{ row }">
        <span class="font-semibold tabular-nums">
          {{ row.on_hand_delta !== 0 ? signed(row.on_hand_delta) : '' }}
          <span
            v-if="row.reserved_delta !== 0"
            class="block text-xs font-normal text-text-secondary"
          >
            {{ t('inventory.movements.reservedDelta', { delta: signed(row.reserved_delta) }) }}
          </span>
        </span>
      </template>
      <template #cell-after="{ row }">
        <span class="tabular-nums">{{ row.on_hand_after }}</span>
      </template>
      <template #cell-details="{ row }">
        <p class="max-w-64 truncate" :title="row.reason">{{ row.reason || '—' }}</p>
        <p class="text-xs text-text-secondary">
          {{ row.performed_by?.full_name ?? t('inventory.movements.system') }}
        </p>
      </template>
    </DataTable>
  </div>
</template>
