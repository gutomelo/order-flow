<script setup lang="ts">
import { ArrowLeft } from '@lucide/vue'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextAreaField from '@/components/ui/TextAreaField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useIdempotencyKey } from '@/composables/useIdempotencyKey'
import { useAddresses } from '@/modules/customers/composables/useCustomers'
import { useWarehouses } from '@/modules/inventory/composables/useInventory'
import CustomerPicker, { type CustomerOption } from '@/modules/orders/components/CustomerPicker.vue'
import OrderLinesEditor, {
  type EditorLine,
  type LineErrors,
} from '@/modules/orders/components/OrderLinesEditor.vue'
import OrderTotals from '@/modules/orders/components/OrderTotals.vue'
import {
  useOrder,
  usePlaceOrder,
  useQuote,
  useSaveDraft,
  useSubmitOrder,
} from '@/modules/orders/composables/useOrders'
import { formatOrderNumber } from '@/modules/orders/format'
import type { DraftInput, LineInput } from '@/modules/orders/types'
import { ApiError } from '@/services/http/apiError'
import { formatMoney } from '@/utils/money'

/**
 * Novo pedido (`id` ausente) ou edição de rascunho. Preços e totais vêm sempre do backend
 * (`POST /orders/quote`); o envio confirma o total exibido (`expected_total`).
 */
const { id } = defineProps<{ id?: string }>()

const { t } = useI18n()
const router = useRouter()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()

const newLine = (): EditorLine => ({ key: crypto.randomUUID(), product: null, quantity: '1' })

const customer = ref<CustomerOption | null>(null)
const warehouseId = ref('')
const addressId = ref('')
const purchaseOrderNumber = ref('')
const notes = ref('')
const lines = ref<EditorLine[]>([newLine()])

const fieldErrors = ref<{ customer?: string; warehouse?: string; address?: string }>({})
const lineErrors = ref<LineErrors>({})
const formError = ref<string | null>(null)

// Rascunho existente: preenche o formulário uma vez; pedido já enviado não é editável (O6).
const existing = useOrder(() => id)
const loaded = ref(!id)
watch(
  existing.data,
  async (order) => {
    if (!order || loaded.value) return
    if (order.status !== 'DRAFT') {
      await router.replace({ name: 'order-detail', params: { id: order.id } })
      return
    }
    customer.value = {
      id: order.customer.id,
      display_name: order.customer.display_name,
      tax_id_formatted: order.customer.tax_id_formatted,
    }
    warehouseId.value = order.warehouse?.id ?? ''
    addressId.value = order.shipping_address_id ?? ''
    purchaseOrderNumber.value = order.purchase_order_number
    notes.value = order.notes
    lines.value = order.lines.length
      ? order.lines.map((line) => ({
          key: crypto.randomUUID(),
          product: { id: line.product_id, sku: line.sku, name: line.product_name },
          quantity: String(line.quantity),
        }))
      : [newLine()]
    loaded.value = true
  },
  { immediate: true },
)

// Depósitos ativos; com um só, ele já vem escolhido.
const warehouses = useWarehouses()
const activeWarehouses = computed(() => (warehouses.data.value ?? []).filter((w) => w.is_active))
watch(activeWarehouses, (list) => {
  const only = list.length === 1 ? list[0] : undefined
  if (!warehouseId.value && only) warehouseId.value = only.id
})
const warehouseOptions = computed(() => [
  { value: '', label: t('orders.editor.chooseWarehouse') },
  ...activeWarehouses.value.map((w) => ({ value: w.id, label: `${w.code} — ${w.name}` })),
])

// Endereços do cliente: ao trocar de cliente (ou se o escolhido sumiu), volta para a entrega padrão.
const addresses = useAddresses(() => customer.value?.id ?? '')
watch(addresses.data, (list) => {
  if (!list || list.some((address) => address.id === addressId.value)) return
  addressId.value = list.find((address) => address.is_default_shipping)?.id ?? ''
})
const addressOptions = computed(() => [
  { value: '', label: t('orders.editor.chooseAddress') },
  ...(addresses.data.value ?? []).map((a) => ({
    value: a.id,
    label: `${a.label} — ${a.street}, ${a.number} · ${a.city}/${a.state}`,
  })),
])
const customerWithoutAddress = computed(
  () => Boolean(customer.value) && addresses.data.value?.length === 0,
)

// Prévia (debounce de 300 ms enquanto a pessoa digita quantidades).
const requestLines = computed<LineInput[]>(() =>
  lines.value.flatMap((line) =>
    line.product && /^\d+$/.test(line.quantity.trim()) && Number(line.quantity) >= 1
      ? [{ product_id: line.product.id, quantity: Number(line.quantity) }]
      : [],
  ),
)
const quoteInput = computed(() =>
  customer.value ? { customer_id: customer.value.id, lines: requestLines.value } : null,
)
const debouncedQuoteInput = ref(quoteInput.value)
let quoteTimer: ReturnType<typeof setTimeout> | undefined
watch(
  quoteInput,
  (value) => {
    clearTimeout(quoteTimer)
    quoteTimer = setTimeout(() => (debouncedQuoteInput.value = value), 300)
  },
  { deep: true },
)
onBeforeUnmount(() => clearTimeout(quoteTimer))

const quote = useQuote(debouncedQuoteInput)
const quoteMap = computed(
  () =>
    new Map(
      (quote.error.value ? [] : (quote.data.value?.lines ?? [])).map((l) => [l.product_id, l]),
    ),
)
const quoteIsCurrent = computed(
  () => JSON.stringify(debouncedQuoteInput.value) === JSON.stringify(quoteInput.value),
)
const quoteReady = computed(
  () =>
    quoteIsCurrent.value &&
    !quote.isFetching.value &&
    !quote.error.value &&
    Boolean(quote.data.value) &&
    requestLines.value.length > 0,
)
const totals = computed(() =>
  quote.error.value || !requestLines.value.length ? null : quote.data.value,
)

// Erros da prévia por linha (produto sem preço, inativo...).
const quoteLineErrors = computed<LineErrors>(() => {
  const error = quote.error.value
  if (!(error instanceof ApiError) || !Array.isArray(error.details.product_ids)) return {}
  const ids = error.details.product_ids as string[]
  return Object.fromEntries(
    lines.value
      .filter((line) => line.product && ids.includes(line.product.id))
      .map((line) => [line.key, { product: error.message }]),
  )
})
const allLineErrors = computed<LineErrors>(() => ({
  ...quoteLineErrors.value,
  ...lineErrors.value,
}))

function payload(): DraftInput {
  return {
    customer_id: customer.value?.id ?? '',
    warehouse_id: warehouseId.value || null,
    shipping_address_id: addressId.value || null,
    purchase_order_number: purchaseOrderNumber.value.trim(),
    notes: notes.value.trim(),
    lines: requestLines.value,
  }
}

async function focusFirstInvalid() {
  await nextTick()
  const target =
    document.querySelector<HTMLElement>('#order-editor [aria-invalid="true"]') ??
    document.querySelector<HTMLElement>('#order-editor [role="alert"]')
  target?.focus()
}

/** Antecipa as regras do backend; ele continua sendo a autoridade. */
function validate(mode: 'draft' | 'submit'): boolean {
  const fields: typeof fieldErrors.value = {}
  const perLine: LineErrors = {}
  formError.value = null
  if (!customer.value) fields.customer = t('validation.required')
  for (const line of lines.value) {
    if (!line.product) {
      if (mode === 'submit' && lines.value.length > 1)
        perLine[line.key] = { product: t('validation.required') }
      continue
    }
    if (!/^\d+$/.test(line.quantity.trim()) || Number(line.quantity) < 1) {
      perLine[line.key] = { quantity: t('validation.positive') }
    }
  }
  if (mode === 'submit') {
    if (!warehouseId.value) fields.warehouse = t('validation.required')
    if (!addressId.value) fields.address = t('orders.editor.addressRequired')
    if (!requestLines.value.length && !Object.keys(perLine).length) {
      formError.value = t('orders.editor.noLines')
    }
  }
  fieldErrors.value = fields
  lineErrors.value = perLine
  const valid = !Object.keys(fields).length && !Object.keys(perLine).length && !formError.value
  if (!valid) void focusFirstInvalid()
  return valid
}

function applyServerError(error: unknown) {
  if (!(error instanceof ApiError)) {
    formError.value = errorMessage(error)
    return
  }
  const field = error.details.field
  const productIds = error.details.product_ids
  if (field === 'customer_id') fieldErrors.value = { customer: error.message }
  else if (field === 'warehouse_id') fieldErrors.value = { warehouse: error.message }
  else if (field === 'shipping_address_id') fieldErrors.value = { address: error.message }
  else if (Array.isArray(productIds)) {
    const kind = error.code === 'INVALID_QUANTITY' ? 'quantity' : 'product'
    lineErrors.value = Object.fromEntries(
      lines.value
        .filter((line) => line.product && productIds.includes(line.product.id))
        .map((line) => [line.key, { [kind]: error.message }]),
    )
  } else if (error.code === 'PRICES_CHANGED') {
    formError.value = t('orders.editor.pricesChanged', {
      total: formatMoney(String(error.details.actual)),
    })
    void quote.refetch()
  } else formError.value = error.message
  void focusFirstInvalid()
}

const saveDraft = useSaveDraft()
const submitOrder = useSubmitOrder()
const placeOrder = usePlaceOrder()
const busy = computed(
  () => saveDraft.isPending.value || submitOrder.isPending.value || placeOrder.isPending.value,
)
const keyFor = useIdempotencyKey(() => ({
  ...payload(),
  expected_total: quote.data.value?.total ?? null,
}))

async function onSaveDraft() {
  if (busy.value || !validate('draft')) return
  try {
    const order = await saveDraft.mutateAsync({ id, data: payload() })
    toasts.success(t('orders.editor.draftSaved'))
    if (!id) await router.replace({ name: 'order-edit', params: { id: order.id } })
  } catch (error) {
    applyServerError(error)
  }
}

async function onSubmit() {
  if (busy.value || !validate('submit')) return
  if (!quoteReady.value || !quote.data.value) {
    formError.value = t('orders.editor.waitQuote')
    void focusFirstInvalid()
    return
  }
  const expected = quote.data.value.total
  try {
    let order
    if (id) {
      await saveDraft.mutateAsync({ id, data: payload() })
      order = await submitOrder.mutateAsync({ id, expectedTotal: expected })
    } else {
      order = await placeOrder.mutateAsync({
        data: { ...payload(), expected_total: expected },
        key: keyFor(),
      })
    }
    toasts.success(t('orders.editor.submitted', { number: formatOrderNumber(order.number) }))
    await router.push({ name: 'order-detail', params: { id: order.id } })
  } catch (error) {
    applyServerError(error)
  }
}
</script>

<template>
  <div>
    <RouterLink
      :to="{ name: 'orders' }"
      class="mb-4 inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
    >
      <ArrowLeft class="size-4" aria-hidden="true" />
      {{ t('orders.backToList') }}
    </RouterLink>

    <PageHeader
      :title="id ? t('orders.editor.editTitle') : t('orders.editor.newTitle')"
      :description="t('orders.editor.description')"
    />

    <p v-if="!loaded" class="text-sm text-text-secondary" role="status">
      {{ t('common.loading') }}
    </p>
    <form
      v-else
      id="order-editor"
      class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]"
      novalidate
      @submit.prevent="onSubmit"
    >
      <div class="flex min-w-0 flex-col gap-6">
        <FormAlert :message="formError" />

        <section
          aria-labelledby="order-customer-heading"
          class="flex flex-col gap-4 rounded-lg border border-border bg-surface p-5"
        >
          <h2 id="order-customer-heading" class="text-base font-semibold">
            {{ t('orders.editor.customerSection') }}
          </h2>
          <CustomerPicker
            v-model="customer"
            :label="t('orders.fields.customer')"
            :error="fieldErrors.customer"
          />
          <div class="grid gap-4 md:grid-cols-2">
            <SelectField
              v-model="addressId"
              :label="t('orders.fields.shippingAddress')"
              :options="addressOptions"
              :disabled="!customer"
              required
              :help="
                !customer
                  ? t('orders.editor.chooseCustomerFirst')
                  : customerWithoutAddress
                    ? t('orders.editor.customerWithoutAddress')
                    : undefined
              "
              :error="fieldErrors.address"
            />
            <SelectField
              v-model="warehouseId"
              :label="t('orders.fields.warehouse')"
              :options="warehouseOptions"
              required
              :help="t('orders.editor.warehouseHelp')"
              :error="fieldErrors.warehouse"
            />
          </div>
          <RouterLink
            v-if="customerWithoutAddress && customer"
            :to="{ name: 'customer-detail', params: { id: customer.id } }"
            class="text-sm text-link underline-offset-2 hover:underline"
          >
            {{ t('orders.editor.addAddressLink') }}
          </RouterLink>
          <div class="grid gap-4 md:grid-cols-2">
            <TextField
              v-model="purchaseOrderNumber"
              :label="t('orders.fields.purchaseOrderNumber')"
              :help="t('orders.editor.purchaseOrderHelp')"
            />
          </div>
          <TextAreaField v-model="notes" :label="t('orders.fields.notes')" :rows="2" />
        </section>

        <section
          aria-labelledby="order-lines-heading"
          class="flex flex-col gap-4 rounded-lg border border-border bg-surface p-5"
        >
          <h2 id="order-lines-heading" class="text-base font-semibold">
            {{ t('orders.editor.linesSection') }}
          </h2>
          <OrderLinesEditor v-model:lines="lines" :errors="allLineErrors" :quote="quoteMap" />
        </section>
      </div>

      <aside
        aria-labelledby="order-summary-heading"
        class="flex h-fit flex-col gap-4 rounded-lg border border-border bg-surface p-5 lg:sticky lg:top-6"
      >
        <h2 id="order-summary-heading" class="text-base font-semibold">
          {{ t('orders.editor.summary') }}
        </h2>
        <OrderTotals
          :subtotal="totals?.subtotal ?? null"
          :discount-total="totals?.discount_total ?? null"
          :shipping-total="totals?.shipping_total ?? null"
          :total="totals?.total ?? null"
          estimate
        />
        <p class="text-xs text-text-secondary" role="status">
          {{
            !customer
              ? t('orders.editor.quoteNeedsCustomer')
              : quote.isFetching.value || !quoteIsCurrent
                ? t('orders.editor.quoteUpdating')
                : quote.error.value
                  ? t('orders.editor.quoteError')
                  : t('orders.editor.quoteHint')
          }}
        </p>
        <BaseButton
          type="submit"
          :loading="submitOrder.isPending.value || placeOrder.isPending.value"
        >
          {{ t('orders.actions.submit') }}
        </BaseButton>
        <BaseButton variant="secondary" :loading="saveDraft.isPending.value" @click="onSaveDraft">
          {{ t('orders.actions.saveDraft') }}
        </BaseButton>
      </aside>
    </form>
  </div>
</template>
