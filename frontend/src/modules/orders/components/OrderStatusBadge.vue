<script setup lang="ts">
import {
  BadgeCheck,
  CircleCheck,
  CircleX,
  Clock,
  FilePen,
  Hourglass,
  PackageCheck,
  PackageOpen,
  Truck,
  Undo2,
} from '@lucide/vue'
import type { Component } from 'vue'
import { useI18n } from 'vue-i18n'

import StatusBadge from '@/components/ui/StatusBadge.vue'
import type { OrderStatus } from '@/modules/orders/types'

type Tone = 'success' | 'danger' | 'warning' | 'info' | 'neutral'

// Status nunca só por cor: ícone + texto + tom (frontend-ui.md).
const appearance: Record<OrderStatus, { icon: Component; tone: Tone }> = {
  DRAFT: { icon: FilePen, tone: 'neutral' },
  PENDING: { icon: Clock, tone: 'warning' },
  AWAITING_PAYMENT: { icon: Hourglass, tone: 'warning' },
  PAID: { icon: BadgeCheck, tone: 'success' },
  PROCESSING: { icon: PackageOpen, tone: 'info' },
  READY_TO_SHIP: { icon: PackageCheck, tone: 'info' },
  SHIPPED: { icon: Truck, tone: 'info' },
  DELIVERED: { icon: CircleCheck, tone: 'success' },
  CANCELLED: { icon: CircleX, tone: 'danger' },
  REFUNDED: { icon: Undo2, tone: 'neutral' },
}

const { status } = defineProps<{ status: OrderStatus }>()
const { t } = useI18n()
</script>

<template>
  <StatusBadge
    :label="t(`orders.status.${status}`)"
    :icon="appearance[status].icon"
    :tone="appearance[status].tone"
  />
</template>
