<script setup lang="ts">
import {
  ArrowDownToLine,
  ArrowLeftRight,
  ArrowUpFromLine,
  Lock,
  LockOpen,
  SlidersHorizontal,
  Undo2,
} from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import StatusBadge from '@/components/ui/StatusBadge.vue'
import type { MovementType } from '@/modules/inventory/types'

const { type } = defineProps<{ type: MovementType }>()
const { t } = useI18n()

const presentation = {
  PURCHASE: { icon: ArrowDownToLine, tone: 'success' },
  RETURN: { icon: Undo2, tone: 'success' },
  SALE: { icon: ArrowUpFromLine, tone: 'info' },
  TRANSFER: { icon: ArrowLeftRight, tone: 'info' },
  ADJUSTMENT: { icon: SlidersHorizontal, tone: 'warning' },
  RESERVATION: { icon: Lock, tone: 'neutral' },
  RELEASE: { icon: LockOpen, tone: 'neutral' },
} as const
</script>

<template>
  <StatusBadge
    :label="t(`inventory.movementTypes.${type}`)"
    :icon="presentation[type].icon"
    :tone="presentation[type].tone"
  />
</template>
