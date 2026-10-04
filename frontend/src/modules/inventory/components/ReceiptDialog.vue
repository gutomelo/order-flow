<script setup lang="ts">
import { CircleAlert, Plus, Trash2 } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextAreaField from '@/components/ui/TextAreaField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSessionStore } from '@/modules/auth/stores/session'
import ProductPicker, { type ProductOption } from '@/modules/catalog/components/ProductPicker.vue'
import { useReceiveStock, useWarehouses } from '@/modules/inventory/composables/useInventory'
import { quantity, receiptHeaderSchema } from '@/modules/inventory/schemas/inventoryForms'
import { useSupplierOptions } from '@/modules/suppliers/composables/useSuppliers'
import { ApiError } from '@/services/http/apiError'

/** Entrada de mercadoria com várias linhas; tudo-ou-nada no backend (regra R4). */
const open = defineModel<boolean>('open', { required: true })

const { t } = useI18n()
const toasts = useToastStore()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const warehouses = useWarehouses()
const canSeeSuppliers = session.can('suppliers:read')
const suppliers = canSeeSuppliers ? useSupplierOptions() : null
const receive = useReceiveStock()

const header = useZodForm(receiptHeaderSchema, {
  warehouse_id: '',
  supplier_id: '',
  document_number: '',
  notes: '',
})

interface Line {
  key: number
  product: ProductOption | null
  quantity: string
}
let nextKey = 1
const newLine = (): Line => ({ key: nextKey++, product: null, quantity: '' })
const lines = ref<Line[]>([newLine()])
const lineErrors = ref<Record<number, { product?: string; quantity?: string }>>({})

watch(open, (isOpen) => {
  if (!isOpen) return
  header.reset()
  lines.value = [newLine()]
  lineErrors.value = {}
})

const warehouseOptions = computed(() => [
  { value: '', label: t('inventory.receipt.chooseWarehouse') },
  ...(warehouses.data.value ?? [])
    .filter((warehouse) => warehouse.is_active)
    .map((warehouse) => ({ value: warehouse.id, label: `${warehouse.code} — ${warehouse.name}` })),
])
const supplierOptions = computed(() => [
  { value: '', label: t('inventory.receipt.noSupplier') },
  ...(suppliers?.data.value ?? []).map((supplier) => ({
    value: supplier.id,
    label: supplier.display_name,
  })),
])
const chosenIds = computed(() =>
  lines.value.flatMap((line) => (line.product ? [line.product.id] : [])),
)

function validateLines() {
  const errors: typeof lineErrors.value = {}
  const parsed: { product_id: string; quantity: number }[] = []
  for (const line of lines.value) {
    const lineError: { product?: string; quantity?: string } = {}
    if (!line.product) lineError.product = t('validation.required')
    const qty = quantity(1).safeParse(line.quantity)
    if (!qty.success) lineError.quantity = t(qty.error.issues[0]?.message ?? 'validation.positive')
    if (lineError.product || lineError.quantity) errors[line.key] = lineError
    else if (line.product && qty.success)
      parsed.push({ product_id: line.product.id, quantity: qty.data })
  }
  lineErrors.value = errors
  return Object.keys(errors).length ? null : parsed
}

// Produtos recusados pelo backend (ex.: inativados enquanto o formulário estava aberto).
function markRejectedProducts(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.code !== 'PRODUCT_NOT_AVAILABLE') return false
  const rejected = new Set((error.details.product_ids ?? []) as string[])
  const errors: typeof lineErrors.value = {}
  for (const line of lines.value) {
    if (line.product && rejected.has(line.product.id)) errors[line.key] = { product: error.message }
  }
  lineErrors.value = errors
  return true
}

async function onSubmit() {
  const parsedLines = validateLines()
  if (!parsedLines) {
    header.validate()
    return
  }
  const saved = await header.submit(
    (data) =>
      receive.mutateAsync({
        warehouse_id: data.warehouse_id,
        supplier_id: data.supplier_id || null,
        document_number: data.document_number,
        notes: data.notes,
        lines: parsedLines,
      }),
    (error) => {
      if (!markRejectedProducts(error)) header.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(t('inventory.feedback.received'))
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="t('inventory.receipt.title')"
    :description="t('inventory.receipt.description')"
  >
    <form id="receipt-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <div
        v-if="header.formError.value"
        class="flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm"
        role="alert"
      >
        <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
        {{ header.formError.value }}
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <SelectField
          v-model="header.values.warehouse_id"
          :label="t('inventory.fields.warehouse')"
          :options="warehouseOptions"
          required
          :error="header.errors.value.warehouse_id"
        />
        <SelectField
          v-if="canSeeSuppliers"
          v-model="header.values.supplier_id"
          :label="t('inventory.fields.supplier')"
          :options="supplierOptions"
        />
      </div>
      <TextField
        v-model="header.values.document_number"
        :label="t('inventory.fields.documentNumber')"
        :help="t('inventory.receipt.documentHelp')"
        :error="header.errors.value.document_number"
      />

      <fieldset class="flex flex-col gap-3">
        <legend class="mb-2 text-sm font-medium text-text-primary">
          {{ t('inventory.receipt.lines') }}
        </legend>
        <div
          v-for="(line, index) in lines"
          :key="line.key"
          class="grid grid-cols-[1fr_7rem_auto] items-start gap-2"
        >
          <ProductPicker
            v-model="line.product"
            :label="t('inventory.receipt.lineProduct', { n: index + 1 })"
            hide-label
            :exclude-ids="chosenIds"
            :error="lineErrors[line.key]?.product"
          />
          <TextField
            v-model="line.quantity"
            :label="t('inventory.receipt.lineQuantity', { n: index + 1 })"
            hide-label
            inputmode="numeric"
            :placeholder="t('inventory.fields.quantity')"
            :error="lineErrors[line.key]?.quantity"
          />
          <BaseButton
            variant="ghost"
            size="sm"
            class="mt-0.5"
            :disabled="lines.length === 1"
            @click="lines.splice(index, 1)"
          >
            <Trash2 class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('inventory.receipt.removeLine', { n: index + 1 }) }}</span>
          </BaseButton>
        </div>
        <div>
          <BaseButton variant="secondary" size="sm" @click="lines.push(newLine())">
            <Plus class="size-4" aria-hidden="true" />
            {{ t('inventory.receipt.addLine') }}
          </BaseButton>
        </div>
      </fieldset>

      <TextAreaField v-model="header.values.notes" :label="t('inventory.fields.notes')" :rows="2" />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="header.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="receipt-form" :loading="header.isSubmitting.value">
        {{ t('inventory.receipt.submit') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
