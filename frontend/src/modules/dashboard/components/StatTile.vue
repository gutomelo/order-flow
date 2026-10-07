<script setup lang="ts">
import { Minus, TrendingDown, TrendingUp } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { percentChange } from '@/modules/dashboard/format'

/**
 * Indicador com variação contra o período anterior. A direção vem em ícone + texto (nunca só
 * cor); a cor diz se a mudança é boa (`upIsGood`) — mais estorno é ruim, mais pedido é bom.
 * A cor fica **só no ícone**: texto usa o token de texto (o verde de status tem 3,3:1 no branco,
 * suficiente para um gráfico, não para texto — achado do Lighthouse).
 */
const {
  label,
  value,
  current,
  previous,
  comparedTo,
  period,
  upIsGood = true,
} = defineProps<{
  label: string
  /** Valor já formatado para exibição. */
  value: string
  /** Números para a variação (`null` = sem valor, ex.: ticket médio sem pagamentos). */
  current: number | null
  previous: number | null
  comparedTo: string
  /** Período selecionado (o texto de "sem base" muda com ele). */
  period: string
  upIsGood?: boolean
}>()

const { t } = useI18n()

const change = computed(() =>
  current === null || previous === null ? null : percentChange(current, previous),
)
// Sem base (anterior zerado ou ausente) não há direção a mostrar: fica neutro.
const direction = computed(() => {
  if (change.value === null || current === null || previous === null) return 'flat'
  if (current === previous) return 'flat'
  return current > previous ? 'up' : 'down'
})
const tone = computed(() => {
  if (direction.value === 'flat') return 'text-text-secondary'
  return (direction.value === 'up') === upIsGood ? 'text-success' : 'text-danger'
})
const icon = computed(() => ({ up: TrendingUp, down: TrendingDown, flat: Minus })[direction.value])
const deltaText = computed(() => {
  if (current === null) return t('dashboard.delta.noData')
  if (previous === null || change.value === null) return t(`dashboard.delta.noBase.${period}`)
  if (change.value === 0) return t('dashboard.delta.same', { period: comparedTo })
  const signed = `${change.value > 0 ? '+' : '−'}${Math.abs(change.value)}%`
  return t('dashboard.delta.change', { change: signed, period: comparedTo })
})
</script>

<template>
  <div class="flex flex-col gap-1 rounded-lg border border-border bg-surface p-4">
    <p class="text-sm text-text-secondary">{{ label }}</p>
    <p class="text-2xl font-semibold tracking-tight text-text-primary">{{ value }}</p>
    <p class="flex items-center gap-1 text-xs text-text-secondary">
      <component :is="icon" class="size-3.5 shrink-0" :class="tone" aria-hidden="true" />
      <span>{{ deltaText }}</span>
    </p>
  </div>
</template>
