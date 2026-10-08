<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import type { AuditLog } from '@/modules/audit/types'
import { formatMoney } from '@/utils/money'

/** "Status: Pago → Cancelado", "Saldo físico: 10 → 7", "Valor: R$ 13,00". */
const { log } = defineProps<{ log: AuditLog }>()
const { t, te } = useI18n()

const STATUS_KEYS: Record<string, string> = {
  ORDER: 'orders.status',
  PAYMENT: 'payments.paymentStatus',
  REFUND: 'payments.refundStatus',
}

function display(field: string, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (field === 'amount') return formatMoney(String(value))
  if (field === 'method') return t(`payments.method.${String(value)}`)
  if (field === 'status') {
    const key = `${STATUS_KEYS[log.entity_type] ?? ''}.${String(value)}`
    return te(key) ? t(key) : String(value)
  }
  return String(value)
}

// O `jsonb` do PostgreSQL reordena as chaves; aqui a ordem é a de leitura (status primeiro).
const ORDER = ['status', 'on_hand', 'reserved', 'reorder_point', 'amount', 'method']
const rank = (field: string) => (ORDER.includes(field) ? ORDER.indexOf(field) : ORDER.length)

const lines = computed(() =>
  Object.entries(log.changes)
    .sort(([a], [b]) => rank(a) - rank(b))
    .map(([field, value]) => {
      const label = te(`audit.fields.${field}`) ? t(`audit.fields.${field}`) : field
      if (Array.isArray(value) && value.length === 2) {
        return { field, label, text: `${display(field, value[0])} → ${display(field, value[1])}` }
      }
      return { field, label, text: display(field, value) }
    }),
)
</script>

<template>
  <ul class="flex flex-col gap-0.5 text-xs">
    <li v-for="line in lines" :key="line.field">
      <span class="text-text-secondary">{{ line.label }}:</span> {{ line.text }}
    </li>
    <li v-if="log.reason" class="text-text-secondary">“{{ log.reason }}”</li>
  </ul>
</template>
