<script setup lang="ts">
import { Truck } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { ORDERS_PAGE_SIZE } from '@/modules/orders/api/ordersApi'
import FulfillmentActionButton from '@/modules/orders/components/FulfillmentActionButton.vue'
import { useOrdersList } from '@/modules/orders/composables/useOrders'
import { formatOrderNumber } from '@/modules/orders/format'
import type { OrderStatus } from '@/modules/orders/types'
import { formatDateTime } from '@/utils/datetime'

/** Fila da expedição: uma aba por etapa, mais antigos primeiro, com o próximo passo na linha. */
const QUEUES = ['PAID', 'PROCESSING', 'READY_TO_SHIP', 'SHIPPED'] as const
type Queue = (typeof QUEUES)[number]

const { t } = useI18n()
const errorMessage = useApiErrorMessage()

const { filters, field } = useUrlFilters<{ page: number; status: Queue }>(
  { page: 1, status: 'PAID' },
  { status: (raw) => (QUEUES.includes(raw as Queue) ? (raw as Queue) : undefined) },
)
const status = field('status')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useOrdersList(() => ({
  page: filters.value.page,
  search: '',
  status: filters.value.status as OrderStatus,
  ordering: 'submitted_at' as const,
}))

const columns = computed(() => [
  { key: 'number', label: t('orders.fields.number') },
  { key: 'customer', label: t('orders.fields.customer') },
  { key: 'items', label: t('orders.fulfillment.queue.items'), align: 'right' as const },
  { key: 'date', label: t('orders.fulfillment.queue.since') },
  { key: 'action', label: t('orders.fulfillment.queue.nextStep'), srOnly: true },
])
</script>

<template>
  <div>
    <PageHeader
      :title="t('orders.fulfillment.queue.title')"
      :description="t('orders.fulfillment.queue.description')"
    />

    <nav class="mb-4 flex flex-wrap gap-2" :aria-label="t('orders.fulfillment.queue.tabsLabel')">
      <button
        v-for="queue in QUEUES"
        :key="queue"
        type="button"
        class="h-9 rounded-md border px-3 text-sm font-medium"
        :class="
          status === queue
            ? 'border-primary bg-primary text-on-primary'
            : 'border-border bg-surface text-text-primary hover:bg-surface-muted'
        "
        :aria-pressed="status === queue"
        @click="status = queue"
      >
        {{ t(`orders.fulfillment.queue.tabs.${queue}`) }}
      </button>
    </nav>

    <DataTable
      v-model:page="page"
      :caption="t(`orders.fulfillment.queue.tabs.${status}`)"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="ORDERS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('orders.error.title')"
      :empty-title="t('orders.fulfillment.queue.emptyTitle')"
      :empty-description="t(`orders.fulfillment.queue.empty.${status}`)"
      :empty-icon="Truck"
      @retry="refetch()"
    >
      <template #cell-number="{ row }">
        <RouterLink
          :to="{ name: 'order-detail', params: { id: row.id } }"
          class="font-medium text-link tabular-nums underline-offset-2 hover:underline"
        >
          {{ formatOrderNumber(row.number) }}
        </RouterLink>
      </template>
      <template #cell-customer="{ row }">
        <p>{{ row.customer.display_name }}</p>
        <p class="text-xs text-text-secondary tabular-nums">{{ row.customer.tax_id_formatted }}</p>
      </template>
      <template #cell-items="{ row }">
        <span class="tabular-nums">{{ row.lines_count }}</span>
      </template>
      <template #cell-date="{ row }">
        <span class="text-text-secondary">{{ formatDateTime(row.updated_at) }}</span>
      </template>
      <template #cell-action="{ row }">
        <div class="flex justify-end">
          <FulfillmentActionButton :order="row" size="sm" />
        </div>
      </template>
    </DataTable>
  </div>
</template>
