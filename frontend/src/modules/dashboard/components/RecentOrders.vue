<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import type { DashboardData } from '@/modules/dashboard/types'
import OrderStatusBadge from '@/modules/orders/components/OrderStatusBadge.vue'
import type { OrderStatus } from '@/modules/orders/types'
import { formatDateTime } from '@/utils/datetime'
import { formatMoney } from '@/utils/money'

// O total do pedido é dado do pedido (visível a quem lê pedidos, como na lista); só os
// indicadores agregados de dinheiro exigem `reports:financial`.
const { orders } = defineProps<{ orders: DashboardData['orders']['recent'] }>()
const { t } = useI18n()
</script>

<template>
  <section aria-labelledby="recent-heading" class="rounded-lg border border-border bg-surface p-5">
    <div class="mb-3 flex items-baseline justify-between gap-3">
      <h2 id="recent-heading" class="text-base font-semibold">
        {{ t('dashboard.recent.title') }}
      </h2>
      <RouterLink
        :to="{ name: 'orders' }"
        class="text-sm text-link underline-offset-2 hover:underline"
      >
        {{ t('dashboard.recent.all') }}
      </RouterLink>
    </div>
    <p v-if="!orders.length" class="text-sm text-text-secondary">
      {{ t('dashboard.recent.empty') }}
    </p>
    <div v-else class="overflow-x-auto">
      <table class="w-full min-w-[480px] text-sm">
        <caption class="sr-only">
          {{
            t('dashboard.recent.title')
          }}
        </caption>
        <thead>
          <tr class="border-b border-border text-left text-xs text-text-secondary">
            <th scope="col" class="py-2 pr-3 font-medium">{{ t('orders.fields.number') }}</th>
            <th scope="col" class="py-2 pr-3 font-medium">{{ t('orders.fields.customer') }}</th>
            <th scope="col" class="py-2 pr-3 font-medium">{{ t('common.status.label') }}</th>
            <th scope="col" class="py-2 pr-3 text-right font-medium">
              {{ t('orders.totals.total') }}
            </th>
            <th scope="col" class="py-2 font-medium">{{ t('orders.fields.date') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in orders" :key="order.id" class="border-b border-border">
            <td class="py-2 pr-3">
              <RouterLink
                :to="{ name: 'order-detail', params: { id: order.id } }"
                class="font-medium text-link tabular-nums underline-offset-2 hover:underline"
              >
                {{ order.reference }}
              </RouterLink>
            </td>
            <td class="py-2 pr-3">{{ order.customer_name }}</td>
            <td class="py-2 pr-3"><OrderStatusBadge :status="order.status as OrderStatus" /></td>
            <td class="py-2 pr-3 text-right tabular-nums">
              {{ formatMoney(order.total) }}
            </td>
            <td class="py-2 text-text-secondary">{{ formatDateTime(order.submitted_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
