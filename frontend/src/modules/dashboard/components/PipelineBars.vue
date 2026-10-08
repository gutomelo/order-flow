<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { formatCount } from '@/modules/dashboard/format'

/** Funil atual: quantos pedidos em cada etapa. Barras horizontais com o valor na ponta; cada
 * linha é um link para a lista de pedidos filtrada por aquele status. */
const { rows } = defineProps<{ rows: { status: string; count: number }[] }>()
const { t } = useI18n()
const max = computed(() => Math.max(1, ...rows.map((row) => row.count)))
</script>

<template>
  <section
    aria-labelledby="pipeline-heading"
    class="rounded-lg border border-border bg-surface p-5"
  >
    <h2 id="pipeline-heading" class="text-base font-semibold">
      {{ t('dashboard.pipeline.title') }}
    </h2>
    <p class="mb-4 text-sm text-text-secondary">{{ t('dashboard.pipeline.description') }}</p>
    <ul class="flex flex-col gap-2 text-sm">
      <li v-for="row in rows" :key="row.status">
        <RouterLink
          :to="{ name: 'orders', query: { status: row.status } }"
          class="grid grid-cols-[minmax(0,10rem)_1fr] items-center gap-3 rounded px-1 py-0.5 hover:bg-surface-muted"
        >
          <span class="truncate">{{ t(`orders.status.${row.status}`) }}</span>
          <span class="flex items-center gap-2">
            <span
              class="h-3 rounded-r-[4px] bg-chart-bar"
              :style="{ width: `${(row.count / max) * 85}%`, minWidth: row.count ? '2px' : '0' }"
              aria-hidden="true"
            />
            <span class="tabular-nums text-text-primary">{{ formatCount(row.count) }}</span>
          </span>
        </RouterLink>
      </li>
    </ul>
  </section>
</template>
