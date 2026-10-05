<script setup lang="ts">
import { Plus, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import TextField from '@/components/ui/TextField.vue'
import ProductPicker, { type ProductOption } from '@/modules/catalog/components/ProductPicker.vue'
import type { QuoteLine } from '@/modules/orders/types'
import { formatMoney } from '@/utils/money'

export interface EditorLine {
  key: string
  product: ProductOption | null
  quantity: string
}

export type LineErrors = Record<string, { product?: string; quantity?: string }>

/** Itens do rascunho: produto, quantidade e o preço que o backend cotou para cada linha. */
const lines = defineModel<EditorLine[]>('lines', { required: true })
const { errors, quote } = defineProps<{
  errors: LineErrors
  /** Cotação por produto (prévia do backend); ausente enquanto não há cotação válida. */
  quote: Map<string, QuoteLine>
}>()

const { t } = useI18n()

function addLine() {
  lines.value.push({ key: crypto.randomUUID(), product: null, quantity: '1' })
}

function removeLine(index: number) {
  lines.value.splice(index, 1)
}

const otherProductIds = (line: EditorLine) =>
  lines.value
    .filter((other) => other !== line && other.product)
    .map((other) => other.product?.id ?? '')

const quoted = (line: EditorLine) => (line.product ? quote.get(line.product.id) : undefined)
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="overflow-x-auto">
      <table class="w-full min-w-[680px] text-sm">
        <caption class="sr-only">
          {{
            t('orders.editor.linesCaption')
          }}
        </caption>
        <thead>
          <tr class="border-b border-border text-left text-xs text-text-secondary">
            <th scope="col" class="py-2 pr-3 font-medium">{{ t('orders.fields.product') }}</th>
            <th scope="col" class="w-28 py-2 pr-3 font-medium">
              {{ t('orders.fields.quantity') }}
            </th>
            <th scope="col" class="w-32 py-2 pr-3 text-right font-medium">
              {{ t('orders.fields.unitPrice') }}
            </th>
            <th scope="col" class="w-32 py-2 pr-3 text-right font-medium">
              {{ t('orders.fields.lineTotal') }}
            </th>
            <th scope="col" class="w-12 py-2">
              <span class="sr-only">{{ t('common.actions') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(line, index) in lines"
            :key="line.key"
            class="border-b border-border align-top"
          >
            <td class="py-2 pr-3">
              <ProductPicker
                v-model="line.product"
                hide-label
                :label="t('orders.editor.lineProduct', { n: index + 1 })"
                :error="errors[line.key]?.product"
                :exclude-ids="otherProductIds(line)"
              />
            </td>
            <td class="py-2 pr-3">
              <TextField
                v-model="line.quantity"
                hide-label
                inputmode="numeric"
                :label="t('orders.editor.lineQuantity', { n: index + 1 })"
                :error="errors[line.key]?.quantity"
              />
            </td>
            <td class="py-2 pr-3 pt-4 text-right tabular-nums">
              {{ quoted(line) ? formatMoney(quoted(line)?.unit_price) : '—' }}
            </td>
            <td class="py-2 pr-3 pt-4 text-right font-medium tabular-nums">
              {{ quoted(line) ? formatMoney(quoted(line)?.line_total) : '—' }}
            </td>
            <td class="py-2">
              <BaseButton
                variant="ghost"
                size="sm"
                :disabled="lines.length === 1"
                @click="removeLine(index)"
              >
                <Trash2 class="size-4" aria-hidden="true" />
                <span class="sr-only">{{ t('orders.editor.removeLine', { n: index + 1 }) }}</span>
              </BaseButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div>
      <BaseButton variant="secondary" size="sm" @click="addLine">
        <Plus class="size-4" aria-hidden="true" />
        {{ t('orders.editor.addLine') }}
      </BaseButton>
    </div>
  </div>
</template>
