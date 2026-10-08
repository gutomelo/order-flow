<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import BarChart from '@/modules/dashboard/components/BarChart.vue'
import PipelineBars from '@/modules/dashboard/components/PipelineBars.vue'
import RecentOrders from '@/modules/dashboard/components/RecentOrders.vue'
import StatTile from '@/modules/dashboard/components/StatTile.vue'
import SystemHealthCard from '@/modules/dashboard/components/SystemHealthCard.vue'
import { useDashboard } from '@/modules/dashboard/composables/useDashboard'
import { formatCount, slotLabel } from '@/modules/dashboard/format'
import type { DashboardPeriod } from '@/modules/dashboard/types'
import { formatTime } from '@/utils/datetime'
import { formatMoney } from '@/utils/money'

const PERIODS: DashboardPeriod[] = ['today', '7d', '30d']

const { t } = useI18n()
const errorMessage = useApiErrorMessage()

const { filters, field } = useUrlFilters<{ page: number; period: DashboardPeriod }>(
  { page: 1, period: '7d' },
  {
    period: (raw) =>
      PERIODS.includes(raw as DashboardPeriod) ? (raw as DashboardPeriod) : undefined,
  },
)
const period = field('period')
const { data, isPending, isFetching, error, refetch } = useDashboard(() => filters.value.period)

const comparedTo = computed(() => t(`dashboard.periods.previous.${filters.value.period}`))
const num = (value: string | null) => (value === null ? null : Number(value))

const salesChart = computed(() => {
  const d = data.value
  if (!d) return []
  if (d.money) {
    return d.money.series.map((slot) => ({
      label: slotLabel(slot.start, d.bucket),
      value: Number(slot.net),
      display: formatMoney(slot.net),
    }))
  }
  return d.orders.series.map((slot) => ({
    label: slotLabel(slot.start, d.bucket),
    value: slot.count,
    display: formatCount(slot.count),
  }))
})
</script>

<template>
  <div>
    <PageHeader :title="t('dashboard.title')" :description="t('dashboard.description')" />

    <!-- Filtro numa linha acima de tudo: ele vale para todos os números da página. -->
    <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap gap-2" role="group" :aria-label="t('dashboard.periods.label')">
        <button
          v-for="option in PERIODS"
          :key="option"
          type="button"
          class="h-9 rounded-md border px-3 text-sm font-medium"
          :class="
            period === option
              ? 'border-primary bg-primary text-on-primary'
              : 'border-border bg-surface text-text-primary hover:bg-surface-muted'
          "
          :aria-pressed="period === option"
          @click="period = option"
        >
          {{ t(`dashboard.periods.${option}`) }}
        </button>
      </div>
      <p v-if="data" class="text-xs text-text-secondary" role="status">
        {{ t('dashboard.updatedAt', { time: formatTime(new Date(data.generated_at)) }) }}
      </p>
    </div>

    <p v-if="isPending" class="text-sm text-text-secondary" role="status">
      {{ t('common.loading') }}
    </p>
    <div v-else-if="error && !data" class="flex flex-wrap items-center gap-3 text-sm" role="alert">
      <span>{{ errorMessage(error) }}</span>
      <BaseButton size="sm" variant="secondary" @click="refetch()">{{
        t('common.retry')
      }}</BaseButton>
    </div>

    <!-- Atualizando: mantém os números anteriores esmaecidos (sem pular a tela). -->
    <div
      v-else-if="data"
      class="flex flex-col gap-6 transition-opacity"
      :class="{ 'opacity-60': isFetching }"
      :aria-busy="isFetching"
    >
      <div class="grid grid-cols-[repeat(auto-fit,minmax(12rem,1fr))] gap-4">
        <StatTile
          :label="t('dashboard.tiles.orders')"
          :value="formatCount(data.orders.submitted.value)"
          :current="data.orders.submitted.value"
          :previous="data.orders.submitted.previous"
          :compared-to="comparedTo"
          :period="filters.period"
        />
        <template v-if="data.money">
          <StatTile
            :label="t('dashboard.tiles.revenue')"
            :value="formatMoney(data.money.revenue.value)"
            :current="num(data.money.revenue.value)"
            :previous="num(data.money.revenue.previous)"
            :compared-to="comparedTo"
            :period="filters.period"
          />
          <StatTile
            :label="t('dashboard.tiles.averageTicket')"
            :value="formatMoney(data.money.average_ticket.value)"
            :current="num(data.money.average_ticket.value)"
            :previous="num(data.money.average_ticket.previous)"
            :compared-to="comparedTo"
            :period="filters.period"
          />
          <StatTile
            :label="t('dashboard.tiles.refunded')"
            :value="formatMoney(data.money.refunded.value)"
            :current="num(data.money.refunded.value)"
            :previous="num(data.money.refunded.previous)"
            :compared-to="comparedTo"
            :period="filters.period"
            :up-is-good="false"
          />
        </template>
        <RouterLink
          v-if="data.stock"
          :to="{ name: 'stock', query: { low: 'true' } }"
          class="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4 hover:bg-surface-muted"
        >
          <span class="text-sm text-text-secondary">{{ t('dashboard.tiles.lowStock') }}</span>
          <span class="text-2xl font-semibold tracking-tight text-text-primary">
            {{ formatCount(data.stock.low_stock_items) }}
          </span>
          <span class="text-xs text-link">{{ t('dashboard.tiles.lowStockLink') }}</span>
        </RouterLink>
      </div>

      <div class="grid gap-6 xl:grid-cols-3">
        <section class="min-w-0 rounded-lg border border-border bg-surface p-5 xl:col-span-2">
          <BarChart
            :title="
              data.money ? t('dashboard.chart.revenueTitle') : t('dashboard.chart.ordersTitle')
            "
            :data="salesChart"
            :value-header="data.money ? t('dashboard.chart.revenue') : t('dashboard.chart.orders')"
          />
          <p v-if="data.money" class="mt-2 text-xs text-text-secondary">
            {{ t('dashboard.chart.revenueNote') }}
          </p>
        </section>
        <PipelineBars :rows="data.orders.open_by_status" />
      </div>

      <div class="grid gap-6 xl:grid-cols-3">
        <!-- min-w-0: a tabela rola dentro do card em vez de alargar a página (achado no celular). -->
        <div class="min-w-0 xl:col-span-2">
          <RecentOrders :orders="data.orders.recent" />
        </div>
        <SystemHealthCard />
      </div>
    </div>
  </div>
</template>
