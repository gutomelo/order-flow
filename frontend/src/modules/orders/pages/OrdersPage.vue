<script setup lang="ts">
import { Plus, ShoppingCart } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useSessionStore } from '@/modules/auth/stores/session'
import { ORDERS_PAGE_SIZE } from '@/modules/orders/api/ordersApi'
import OrderStatusBadge from '@/modules/orders/components/OrderStatusBadge.vue'
import { useOrdersList } from '@/modules/orders/composables/useOrders'
import { formatOrderNumber } from '@/modules/orders/format'
import type { OrderFilters, OrderStatus } from '@/modules/orders/types'
import { formatDateTime } from '@/utils/datetime'
import { formatMoney } from '@/utils/money'

const STATUSES: OrderStatus[] = [
  'DRAFT',
  'PENDING',
  'AWAITING_PAYMENT',
  'PAID',
  'PROCESSING',
  'READY_TO_SHIP',
  'SHIPPED',
  'DELIVERED',
  'CANCELLED',
  'REFUNDED',
]

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canCreate = computed(() => session.can('orders:create'))

const { filters, field, hasActiveFilters } = useUrlFilters<OrderFilters>(
  { page: 1, search: '', status: '' },
  { status: (raw) => (STATUSES.includes(raw as OrderStatus) ? (raw as OrderStatus) : undefined) },
)
const search = field('search')
const status = field('status')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useOrdersList(filters)

const statusOptions = computed(() => [
  { value: '', label: t('common.allStatuses') },
  ...STATUSES.map((value) => ({ value, label: t(`orders.status.${value}`) })),
])
const columns = computed(() => [
  { key: 'number', label: t('orders.fields.number') },
  { key: 'customer', label: t('orders.fields.customer') },
  { key: 'status', label: t('common.status.label') },
  { key: 'total', label: t('orders.totals.total'), align: 'right' as const },
  { key: 'date', label: t('orders.fields.date') },
])
</script>

<template>
  <div>
    <PageHeader :title="t('orders.title')" :description="t('orders.description')">
      <template v-if="canCreate" #actions>
        <RouterLink
          :to="{ name: 'order-new' }"
          class="inline-flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-on-primary hover:bg-primary-hover"
        >
          <Plus class="size-4" aria-hidden="true" />
          {{ t('orders.actions.create') }}
        </RouterLink>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('orders.filters.search')" />
      <SelectField
        v-model="status"
        :label="t('common.status.label')"
        :options="statusOptions"
        hide-label
      />
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('orders.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="ORDERS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('orders.error.title')"
      :empty-title="t('orders.empty.title')"
      :empty-description="t('orders.empty.description')"
      :empty-icon="ShoppingCart"
      :filtered="hasActiveFilters"
      @retry="refetch()"
    >
      <template v-if="canCreate" #empty-action>
        <RouterLink
          :to="{ name: 'order-new' }"
          class="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-on-primary hover:bg-primary-hover"
        >
          {{ t('orders.actions.create') }}
        </RouterLink>
      </template>
      <template #cell-number="{ row }">
        <RouterLink
          :to="{ name: 'order-detail', params: { id: row.id } }"
          class="font-medium text-link tabular-nums underline-offset-2 hover:underline"
        >
          {{ formatOrderNumber(row.number) ?? t('orders.noNumber') }}
        </RouterLink>
        <p v-if="row.purchase_order_number" class="text-xs text-text-secondary">
          {{ t('orders.poShort', { po: row.purchase_order_number }) }}
        </p>
      </template>
      <template #cell-customer="{ row }">
        <p>{{ row.customer.display_name }}</p>
        <p class="text-xs text-text-secondary tabular-nums">{{ row.customer.tax_id_formatted }}</p>
      </template>
      <template #cell-status="{ row }">
        <OrderStatusBadge :status="row.status" />
      </template>
      <template #cell-total="{ row }">
        <span class="tabular-nums">{{ formatMoney(row.total) }}</span>
      </template>
      <template #cell-date="{ row }">
        <span class="text-text-secondary">
          {{ formatDateTime(row.submitted_at ?? row.created_at) }}
        </span>
      </template>
    </DataTable>
  </div>
</template>
