<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextAreaField from '@/components/ui/TextAreaField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { getStockItem } from '@/modules/inventory/api/inventoryApi'
import { useAdjustStock } from '@/modules/inventory/composables/useInventory'
import { adjustmentSchema } from '@/modules/inventory/schemas/inventoryForms'
import type { StockItem } from '@/modules/inventory/types'
import { ApiError } from '@/services/http/apiError'

/**
 * Ajuste por contagem física. O saldo exibido ao abrir é enviado como `expected_on_hand`:
 * se o item foi movimentado durante a contagem, o backend recusa (regra A2) em vez de
 * sobrescrever a movimentação. Nesse caso o diálogo recarrega o item e passa a exibir o
 * saldo novo: o próximo envio usa esse saldo, depois que a pessoa já o viu e conferiu a contagem.
 */
const open = defineModel<boolean>('open', { required: true })
const { item } = defineProps<{ item: StockItem }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const adjust = useAdjustStock()

// Saldo que a pessoa está vendo; só muda quando o backend aponta que ficou desatualizado.
const current = shallowRef<StockItem>(item)
const form = useZodForm(adjustmentSchema, { counted_quantity: '', reason: '' })

watch(open, (isOpen) => {
  if (isOpen) form.reset()
})

const difference = computed(() => {
  const counted = Number(form.values.counted_quantity)
  return form.values.counted_quantity.trim() !== '' && Number.isInteger(counted)
    ? counted - current.value.on_hand
    : null
})

async function refreshAfterConflict(error: ApiError) {
  const before = current.value.on_hand
  try {
    current.value = await getStockItem(current.value.id)
    form.formError.value = t('inventory.adjust.stockChanged', {
      before,
      after: current.value.on_hand,
    })
  } catch {
    // Sem o saldo novo não há o que conferir: mantém a mensagem original do backend.
    form.formError.value = errorMessage(error)
  }
}

async function onSubmit() {
  const saved = await form.submit(
    (data) =>
      adjust.mutateAsync({
        stock_item_id: current.value.id,
        counted_quantity: data.counted_quantity,
        expected_on_hand: current.value.on_hand,
        reason: data.reason,
      }),
    async (error) => {
      if (error instanceof ApiError && error.code === 'STOCK_CHANGED_SINCE_COUNT') {
        await refreshAfterConflict(error)
        return
      }
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(t('inventory.feedback.adjusted'))
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="t('inventory.adjust.title')"
    :description="`${item.product.sku} — ${item.product.name} · ${item.warehouse.code}`"
  >
    <form id="adjust-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />

      <dl class="grid grid-cols-3 gap-2 rounded-md bg-surface-muted p-3 text-sm tabular-nums">
        <div>
          <dt class="text-xs text-text-secondary">{{ t('inventory.fields.onHand') }}</dt>
          <dd class="font-semibold">{{ current.on_hand }}</dd>
        </div>
        <div>
          <dt class="text-xs text-text-secondary">{{ t('inventory.fields.reserved') }}</dt>
          <dd class="font-semibold">{{ current.reserved }}</dd>
        </div>
        <div>
          <dt class="text-xs text-text-secondary">{{ t('inventory.adjust.difference') }}</dt>
          <dd class="font-semibold" aria-live="polite">
            {{ difference === null ? '—' : difference > 0 ? `+${difference}` : difference }}
          </dd>
        </div>
      </dl>

      <TextField
        v-model="form.values.counted_quantity"
        :label="t('inventory.adjust.counted')"
        inputmode="numeric"
        required
        :help="t('inventory.adjust.countedHelp')"
        :error="form.errors.value.counted_quantity"
      />
      <TextAreaField
        v-model="form.values.reason"
        :label="t('inventory.fields.reason')"
        :help="t('inventory.adjust.reasonHelp')"
        :error="form.errors.value.reason"
        :rows="2"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="adjust-form" :loading="form.isSubmitting.value">
        {{ t('inventory.adjust.submit') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
