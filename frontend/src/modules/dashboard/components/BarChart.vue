<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useId, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * Colunas de uma série só (SVG próprio, sem biblioteca): barras de até 24px com o topo arredondado,
 * grade discreta, um tooltip por barra no mouse e no teclado (setas) e a mesma informação numa
 * tabela. Sem legenda — o título diz o que é a série. Valores negativos descem da linha de base.
 */
export interface BarDatum {
  label: string
  value: number
  /** Texto do valor (dinheiro, contagem) já formatado. */
  display: string
}

const { title, data, valueHeader } = defineProps<{
  title: string
  data: BarDatum[]
  valueHeader: string
}>()

const { t } = useI18n()
const id = useId()
const container = useTemplateRef<HTMLDivElement>('container')
const width = ref(640)
const HEIGHT = 220
const PADDING = { top: 12, right: 8, bottom: 28, left: 56 }

let observer: ResizeObserver | undefined
onMounted(() => {
  if (!container.value || typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(([entry]) => {
    if (entry) width.value = Math.max(280, Math.floor(entry.contentRect.width))
  })
  observer.observe(container.value)
})
onBeforeUnmount(() => observer?.disconnect())

/** Escala "redonda" (0, 50, 100…) que cobre o maior e o menor valor. */
function niceStep(range: number): number {
  const raw = range / 4
  const power = 10 ** Math.floor(Math.log10(raw || 1))
  const fraction = raw / power
  return (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * power
}
const scale = computed(() => {
  const values = data.map((d) => d.value)
  const max = Math.max(0, ...values)
  const min = Math.min(0, ...values)
  const step = niceStep(max - min || 1)
  const top = Math.ceil(max / step) * step || step
  const bottom = Math.floor(min / step) * step
  const ticks: number[] = []
  for (let v = bottom; v <= top + step / 2; v += step) ticks.push(Number(v.toFixed(6)))
  return { top, bottom, ticks }
})
const plot = computed(() => ({
  width: width.value - PADDING.left - PADDING.right,
  height: HEIGHT - PADDING.top - PADDING.bottom,
}))
const y = (value: number) =>
  PADDING.top +
  ((scale.value.top - value) / (scale.value.top - scale.value.bottom)) * plot.value.height
const band = computed(() => plot.value.width / Math.max(1, data.length))
const barWidth = computed(() => Math.max(2, Math.min(24, band.value - 2))) // 2px de ar entre barras

/** Barra com 4px arredondados só na ponta do dado (base reta), para cima ou para baixo. */
function barPath(index: number, value: number): string {
  const x = PADDING.left + index * band.value + (band.value - barWidth.value) / 2
  const base = y(0)
  const end = y(value)
  const h = Math.abs(base - end)
  if (h < 0.5) return ''
  const r = Math.min(4, h, barWidth.value / 2)
  const w = barWidth.value
  if (value >= 0) {
    return `M${x},${base} V${end + r} Q${x},${end} ${x + r},${end} H${x + w - r} Q${x + w},${end} ${x + w},${end + r} V${base} Z`
  }
  return `M${x},${base} V${end - r} Q${x},${end} ${x + r},${end} H${x + w - r} Q${x + w},${end} ${x + w},${end - r} V${base} Z`
}

// Rótulos do eixo X sem colidir: no máximo ~8 visíveis.
const labelEvery = computed(() => Math.max(1, Math.ceil(data.length / 8)))
const tickText = formatTick
function formatTick(value: number): string {
  return new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 }).format(
    value,
  )
}

const active = ref<number | null>(null)
const activeDatum = computed(() => (active.value === null ? null : data[active.value]))
function onPointer(event: PointerEvent) {
  const box = (event.currentTarget as SVGElement).getBoundingClientRect()
  const x = event.clientX - box.left - PADDING.left
  const index = Math.floor(x / band.value)
  active.value = index >= 0 && index < data.length ? index : null
}
function onKey(event: KeyboardEvent) {
  if (!data.length) return
  const last = data.length - 1
  const current = active.value ?? last
  const next = { ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: last }[event.key]
  if (next === undefined) return
  event.preventDefault()
  active.value = Math.min(last, Math.max(0, next))
}
const tooltipLeft = computed(() =>
  active.value === null ? 0 : PADDING.left + (active.value + 0.5) * band.value,
)
</script>

<template>
  <figure class="flex flex-col gap-3">
    <figcaption :id="`${id}-title`" class="text-base font-semibold">{{ title }}</figcaption>
    <div ref="container" class="relative">
      <svg
        :width="width"
        :height="HEIGHT"
        role="img"
        tabindex="0"
        :aria-labelledby="`${id}-title`"
        :aria-describedby="`${id}-hint`"
        class="block max-w-full rounded focus-visible:outline-2 focus-visible:outline-focus-ring"
        @pointermove="onPointer"
        @pointerleave="active = null"
        @keydown="onKey"
        @focus="active = active ?? data.length - 1"
        @blur="active = null"
      >
        <g v-for="tick in scale.ticks" :key="tick">
          <line
            :x1="PADDING.left"
            :x2="width - PADDING.right"
            :y1="y(tick)"
            :y2="y(tick)"
            stroke="var(--color-chart-grid)"
            stroke-width="1"
          />
          <text
            :x="PADDING.left - 8"
            :y="y(tick)"
            text-anchor="end"
            dominant-baseline="middle"
            class="fill-text-secondary text-[11px] tabular-nums"
          >
            {{ tickText(tick) }}
          </text>
        </g>
        <rect
          v-if="active !== null"
          :x="PADDING.left + active * band"
          :y="PADDING.top"
          :width="band"
          :height="plot.height"
          fill="var(--color-surface-muted)"
        />
        <path
          v-for="(datum, index) in data"
          :key="datum.label"
          :d="barPath(index, datum.value)"
          fill="var(--color-chart-bar)"
          :opacity="active === null || active === index ? 1 : 0.55"
        />
        <template v-for="(datum, index) in data" :key="`x-${datum.label}`">
          <text
            v-if="index % labelEvery === 0"
            :x="PADDING.left + (index + 0.5) * band"
            :y="HEIGHT - 8"
            text-anchor="middle"
            class="fill-text-secondary text-[11px]"
          >
            {{ datum.label }}
          </text>
        </template>
      </svg>
      <div
        v-if="activeDatum"
        class="pointer-events-none absolute top-0 -translate-x-1/2 rounded-md border border-border bg-surface px-2 py-1 text-xs shadow-sm"
        :style="{ left: `${tooltipLeft}px` }"
      >
        <p class="font-semibold tabular-nums">{{ activeDatum.display }}</p>
        <p class="text-text-secondary">{{ activeDatum.label }}</p>
      </div>
      <p :id="`${id}-hint`" class="sr-only">{{ t('dashboard.chart.keyboardHint') }}</p>
      <p class="sr-only" aria-live="polite">
        {{ activeDatum ? `${activeDatum.label}: ${activeDatum.display}` : '' }}
      </p>
    </div>
    <details class="text-sm">
      <summary class="cursor-pointer text-link underline-offset-2 hover:underline">
        {{ t('dashboard.chart.showTable') }}
      </summary>
      <table class="mt-2 w-full text-left">
        <caption class="sr-only">
          {{
            title
          }}
        </caption>
        <thead>
          <tr class="border-b border-border text-xs text-text-secondary">
            <th scope="col" class="py-1 font-medium">{{ t('dashboard.chart.slot') }}</th>
            <th scope="col" class="py-1 text-right font-medium">{{ valueHeader }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="datum in data" :key="datum.label" class="border-b border-border">
            <td class="py-1">{{ datum.label }}</td>
            <td class="py-1 text-right tabular-nums">{{ datum.display }}</td>
          </tr>
        </tbody>
      </table>
    </details>
  </figure>
</template>
