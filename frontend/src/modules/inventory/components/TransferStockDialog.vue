<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useTransferStock, useWarehouses } from '@/modules/inventory/composables/useInventory'
import { transferSchema } from '@/modules/inventory/schemas/inventoryForms'
import type { StockItem } from '@/modules/inventory/types'

const open = defineModel<boolean>('open', { required: true })
const { item } = defineProps<{ item: StockItem }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const warehouses = useWarehouses()
const transfer = useTransferStock()

const form = useZodForm(transferSchema, { to_warehouse_id: '', quantity: '', reason: '' })
watch(open, (isOpen) => {
  if (isOpen) form.reset()
})

const destinationOptions = computed(() => [
  { value: '', label: t('inventory.transfer.chooseDestination') },
  ...(warehouses.data.value ?? [])
    .filter((warehouse) => warehouse.is_active && warehouse.id !== item.warehouse.id)
    .map((warehouse) => ({ value: warehouse.id, label: `${warehouse.code} — ${warehouse.name}` })),
])

async function onSubmit() {
  const saved = await form.submit(
    (data) => transfer.mutateAsync({ stock_item_id: item.id, ...data }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(t('inventory.feedback.transferred'))
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="t('inventory.transfer.title')"
    :description="`${item.product.sku} — ${item.product.name} · ${item.warehouse.code}`"
  >
    <form id="transfer-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <div
        v-if="form.formError.value"
        class="flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm"
        role="alert"
      >
        <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
        {{ form.formError.value }}
      </div>
      <SelectField
        v-model="form.values.to_warehouse_id"
        :label="t('inventory.transfer.destination')"
        :options="destinationOptions"
        required
        :error="form.errors.value.to_warehouse_id"
      />
      <TextField
        v-model="form.values.quantity"
        :label="t('inventory.fields.quantity')"
        inputmode="numeric"
        required
        :help="t('inventory.transfer.availableHelp', { available: item.available })"
        :error="form.errors.value.quantity"
      />
      <TextField
        v-model="form.values.reason"
        :label="t('inventory.fields.reason')"
        :error="form.errors.value.reason"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="transfer-form" :loading="form.isSubmitting.value">
        {{ t('inventory.transfer.submit') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
