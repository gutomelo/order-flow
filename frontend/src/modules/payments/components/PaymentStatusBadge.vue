<script setup lang="ts">
import { CircleCheck, CircleX, Hourglass, TriangleAlert, Undo2 } from '@lucide/vue'
import type { Component } from 'vue'
import { useI18n } from 'vue-i18n'

import StatusBadge from '@/components/ui/StatusBadge.vue'
import type { PaymentStatus, RefundStatus } from '@/modules/orders/types'

type Tone = 'success' | 'danger' | 'warning' | 'info' | 'neutral'

// Pagamento e estorno usam o mesmo badge: o `kind` escolhe rótulos e aparência.
const payment: Record<PaymentStatus, { icon: Component; tone: Tone }> = {
  PENDING: { icon: Hourglass, tone: 'warning' },
  APPROVED: { icon: CircleCheck, tone: 'success' },
  DECLINED: { icon: CircleX, tone: 'danger' },
  FAILED: { icon: TriangleAlert, tone: 'danger' },
  REFUNDED: { icon: Undo2, tone: 'neutral' },
}
const refund: Record<RefundStatus, { icon: Component; tone: Tone }> = {
  PENDING: { icon: Hourglass, tone: 'warning' },
  SUCCEEDED: { icon: CircleCheck, tone: 'success' },
  FAILED: { icon: TriangleAlert, tone: 'danger' },
}

const props = defineProps<
  { kind: 'payment'; status: PaymentStatus } | { kind: 'refund'; status: RefundStatus }
>()
const { t } = useI18n()

const look = () =>
  props.kind === 'payment' ? payment[props.status] : refund[props.status as RefundStatus]
</script>

<template>
  <StatusBadge
    :label="t(`payments.${kind}Status.${status}`)"
    :icon="look().icon"
    :tone="look().tone"
  />
</template>
