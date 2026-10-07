<script setup lang="ts">
import { Check, Circle } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import FulfillmentActionButton from '@/modules/orders/components/FulfillmentActionButton.vue'
import { FULFILLMENT_STEPS } from '@/modules/orders/fulfillment'
import type { Order } from '@/modules/orders/types'
import { formatDateTime } from '@/utils/datetime'

/** Expedição do pedido pago: etapas, próximo passo e a remessa (transportadora e rastreio). */
const { order } = defineProps<{ order: Order }>()
const { t } = useI18n()

const reached = computed(() => {
  // Etapa concluída = o histórico já passou por ela (vale também para pedido cancelado no meio).
  const visited = new Set(order.history.map((entry) => entry.to_status))
  return (step: string) => visited.has(step as Order['status'])
})
const stepState = (step: string) =>
  reached.value(step) ? t('orders.fulfillment.stepDone') : t('orders.fulfillment.stepTodo')
const shipment = computed(() => order.shipment)
</script>

<template>
  <section
    aria-labelledby="order-fulfillment-heading"
    class="rounded-lg border border-border bg-surface p-5 text-sm"
  >
    <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
      <h2 id="order-fulfillment-heading" class="text-base font-semibold">
        {{ t('orders.fulfillment.title') }}
      </h2>
      <FulfillmentActionButton :order="order" size="sm" />
    </div>

    <ol class="mb-4 flex flex-col gap-2" :aria-label="t('orders.fulfillment.stepsLabel')">
      <li v-for="step in FULFILLMENT_STEPS" :key="step" class="flex items-center gap-2">
        <Check v-if="reached(step)" class="size-4 text-success" aria-hidden="true" />
        <Circle v-else class="size-4 text-text-secondary" aria-hidden="true" />
        <span :class="reached(step) ? 'text-text-primary' : 'text-text-secondary'">
          {{ t(`orders.fulfillment.steps.${step}`) }}
        </span>
        <!-- Espaço explícito: o compilador do Vue remove o espaço entre os spans. -->
        <span class="sr-only">{{ ` ${stepState(step)}` }}</span>
      </li>
    </ol>

    <dl v-if="shipment" class="flex flex-col gap-3 border-t border-border pt-4">
      <div>
        <dt class="text-xs text-text-secondary">{{ t('orders.fulfillment.carrier') }}</dt>
        <dd>{{ shipment.carrier }}</dd>
      </div>
      <div>
        <dt class="text-xs text-text-secondary">{{ t('orders.fulfillment.trackingCode') }}</dt>
        <dd class="font-mono">{{ shipment.tracking_code }}</dd>
      </div>
      <div>
        <dt class="text-xs text-text-secondary">{{ t('orders.fulfillment.shippedAt') }}</dt>
        <dd>{{ formatDateTime(shipment.shipped_at) }}</dd>
      </div>
      <div v-if="shipment.delivered_at">
        <dt class="text-xs text-text-secondary">{{ t('orders.fulfillment.deliveredAt') }}</dt>
        <dd>
          {{ formatDateTime(shipment.delivered_at) }}
          <span class="block text-xs text-text-secondary">
            {{ t(`orders.fulfillment.deliverySource.${shipment.delivery_source}`) }}
          </span>
          <span v-if="shipment.delivery_note" class="block text-xs text-text-secondary">
            “{{ shipment.delivery_note }}”
          </span>
        </dd>
      </div>
      <p v-else class="text-xs text-text-secondary">{{ t('orders.fulfillment.inTransitHint') }}</p>
    </dl>
  </section>
</template>
