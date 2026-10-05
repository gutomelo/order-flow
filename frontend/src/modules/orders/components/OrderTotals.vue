<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { formatMoney } from '@/utils/money'

defineProps<{
  subtotal: string | null
  discountTotal: string | null
  shippingTotal: string | null
  total: string | null
  /** Rascunho/prévia: valores podem mudar até o envio. */
  estimate?: boolean
}>()

const { t } = useI18n()
</script>

<template>
  <dl class="flex flex-col gap-1 text-sm tabular-nums" aria-live="polite">
    <div class="flex justify-between gap-6">
      <dt class="text-text-secondary">{{ t('orders.totals.subtotal') }}</dt>
      <dd>{{ formatMoney(subtotal) }}</dd>
    </div>
    <div class="flex justify-between gap-6">
      <dt class="text-text-secondary">{{ t('orders.totals.discount') }}</dt>
      <dd>{{ formatMoney(discountTotal) }}</dd>
    </div>
    <div class="flex justify-between gap-6">
      <dt class="text-text-secondary">{{ t('orders.totals.shipping') }}</dt>
      <dd>{{ formatMoney(shippingTotal) }}</dd>
    </div>
    <div
      class="mt-1 flex justify-between gap-6 border-t border-border pt-2 text-base font-semibold"
    >
      <dt>{{ estimate ? t('orders.totals.estimatedTotal') : t('orders.totals.total') }}</dt>
      <dd>{{ formatMoney(total) }}</dd>
    </div>
  </dl>
</template>
