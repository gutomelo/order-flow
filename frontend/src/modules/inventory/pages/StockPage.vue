<script setup lang="ts">
import {
  ArrowLeftRight,
  Boxes,
  CircleAlert,
  CircleCheck,
  History,
  PackagePlus,
  SlidersHorizontal,
  Target,
} from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectField from '@/components/ui/SelectField.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useSessionStore } from '@/modules/auth/stores/session'
import { STOCK_PAGE_SIZE } from '@/modules/inventory/api/inventoryApi'
import AdjustStockDialog from '@/modules/inventory/components/AdjustStockDialog.vue'
import ReceiptDialog from '@/modules/inventory/components/ReceiptDialog.vue'
import ReorderPointDialog from '@/modules/inventory/components/ReorderPointDialog.vue'
import TransferStockDialog from '@/modules/inventory/components/TransferStockDialog.vue'
import { useStockList, useWarehouses } from '@/modules/inventory/composables/useInventory'
import type { StockFilters, StockItem } from '@/modules/inventory/types'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canUpdate = computed(() => session.can('inventory:update'))
const canAdjust = computed(() => session.can('inventory:adjust'))

const { filters, field, hasActiveFilters } = useUrlFilters<StockFilters>(
  { page: 1, search: '', warehouse: '', low: '' },
  { low: (raw) => (raw === 'true' ? 'true' : undefined) },
)
const search = field('search')
const warehouse = field('warehouse')
const low = field('low')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useStockList(filters)
const warehouses = useWarehouses()

const warehouseOptions = computed(() => [
  { value: '', label: t('inventory.filters.allWarehouses') },
  ...(warehouses.data.value ?? []).map((w) => ({ value: w.id, label: `${w.code} — ${w.name}` })),
])
const lowOptions = computed(() => [
  { value: '', label: t('inventory.filters.allLevels') },
  { value: 'true', label: t('inventory.filters.lowOnly') },
])
const columns = computed(() => [
  { key: 'product', label: t('inventory.fields.product') },
  { key: 'warehouse', label: t('inventory.fields.warehouse') },
  { key: 'on_hand', label: t('inventory.fields.onHand'), align: 'right' as const },
  { key: 'reserved', label: t('inventory.fields.reserved'), align: 'right' as const },
  { key: 'available', label: t('inventory.fields.available'), align: 'right' as const },
  { key: 'level', label: t('inventory.fields.level') },
  { key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const },
])

type Action = 'adjust' | 'transfer' | 'reorder'
const active = ref<{ action: Action; item: StockItem } | null>(null)
const dialogOpen = ref(false)
// Recriado a cada abertura: o diálogo captura o saldo exibido naquele momento.
const dialogKey = computed(() =>
  active.value ? `${active.value.action}:${active.value.item.id}:${active.value.item.on_hand}` : '',
)
function open(action: Action, item: StockItem) {
  active.value = { action, item }
  dialogOpen.value = true
}
const receiptOpen = ref(false)
</script>

<template>
  <div>
    <PageHeader :title="t('inventory.stock.title')" :description="t('inventory.stock.description')">
      <template v-if="canUpdate" #actions>
        <BaseButton @click="receiptOpen = true">
          <PackagePlus class="size-4" aria-hidden="true" />
          {{ t('inventory.actions.receive') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('inventory.filters.search')" />
      <SelectField
        v-model="warehouse"
        :label="t('inventory.fields.warehouse')"
        :options="warehouseOptions"
        hide-label
      />
      <SelectField
        v-model="low"
        :label="t('inventory.fields.level')"
        :options="lowOptions"
        hide-label
      />
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('inventory.stock.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="STOCK_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('inventory.stock.errorTitle')"
      :empty-title="t('inventory.stock.emptyTitle')"
      :empty-description="t('inventory.stock.emptyDescription')"
      :empty-icon="Boxes"
      :filtered="hasActiveFilters"
      min-width="880px"
      @retry="refetch()"
    >
      <template v-if="canUpdate" #empty-action>
        <BaseButton @click="receiptOpen = true">{{ t('inventory.actions.receive') }}</BaseButton>
      </template>
      <template #cell-product="{ row }">
        <p class="font-medium">{{ row.product.name }}</p>
        <p class="font-mono text-xs text-text-secondary">{{ row.product.sku }}</p>
      </template>
      <template #cell-warehouse="{ row }">
        <span class="font-mono text-xs">{{ row.warehouse.code }}</span>
      </template>
      <template #cell-on_hand="{ row }"
        ><span class="tabular-nums">{{ row.on_hand }}</span></template
      >
      <template #cell-reserved="{ row }">
        <span class="text-text-secondary tabular-nums">{{ row.reserved }}</span>
      </template>
      <template #cell-available="{ row }">
        <span class="font-semibold tabular-nums">{{ row.available }}</span>
      </template>
      <template #cell-level="{ row }">
        <StatusBadge
          v-if="row.is_low_stock"
          :label="t('inventory.level.low', { point: row.reorder_point })"
          :icon="CircleAlert"
          tone="warning"
        />
        <StatusBadge v-else :label="t('inventory.level.ok')" :icon="CircleCheck" tone="success" />
      </template>
      <template #cell-actions="{ row }">
        <div class="flex justify-end gap-1">
          <BaseButton v-if="canAdjust" variant="ghost" size="sm" @click="open('adjust', row)">
            <SlidersHorizontal class="size-4" aria-hidden="true" />
            <span class="sr-only">{{
              t('inventory.actions.adjustItem', {
                sku: row.product.sku,
                warehouse: row.warehouse.code,
              })
            }}</span>
          </BaseButton>
          <BaseButton
            v-if="canUpdate"
            variant="ghost"
            size="sm"
            :disabled="row.available === 0"
            @click="open('transfer', row)"
          >
            <ArrowLeftRight class="size-4" aria-hidden="true" />
            <span class="sr-only">{{
              t('inventory.actions.transferItem', {
                sku: row.product.sku,
                warehouse: row.warehouse.code,
              })
            }}</span>
          </BaseButton>
          <BaseButton v-if="canUpdate" variant="ghost" size="sm" @click="open('reorder', row)">
            <Target class="size-4" aria-hidden="true" />
            <span class="sr-only">{{
              t('inventory.actions.reorderItem', {
                sku: row.product.sku,
                warehouse: row.warehouse.code,
              })
            }}</span>
          </BaseButton>
          <RouterLink
            :to="{
              name: 'movements',
              query: { product: row.product.id, warehouse: row.warehouse.id },
            }"
            class="inline-flex size-8 items-center justify-center rounded-md text-text-secondary hover:bg-surface-muted hover:text-text-primary"
          >
            <History class="size-4" aria-hidden="true" />
            <span class="sr-only">{{
              t('inventory.actions.historyItem', {
                sku: row.product.sku,
                warehouse: row.warehouse.code,
              })
            }}</span>
          </RouterLink>
        </div>
      </template>
    </DataTable>

    <ReceiptDialog v-if="canUpdate" v-model:open="receiptOpen" />
    <template v-if="active">
      <AdjustStockDialog
        v-if="active.action === 'adjust'"
        :key="dialogKey"
        v-model:open="dialogOpen"
        :item="active.item"
      />
      <TransferStockDialog
        v-else-if="active.action === 'transfer'"
        :key="dialogKey"
        v-model:open="dialogOpen"
        :item="active.item"
      />
      <ReorderPointDialog v-else :key="dialogKey" v-model:open="dialogOpen" :item="active.item" />
    </template>
  </div>
</template>
