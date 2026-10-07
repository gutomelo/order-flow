<script setup lang="ts">
import { ArrowLeft, PackageCheck, Pencil, Send, TriangleAlert, XCircle } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useSessionStore } from '@/modules/auth/stores/session'
import { formatPostalCode } from '@/modules/customers/addresses'
import CancelOrderDialog from '@/modules/orders/components/CancelOrderDialog.vue'
import OrderFulfillmentPanel from '@/modules/orders/components/OrderFulfillmentPanel.vue'
import OrderPaymentPanel from '@/modules/orders/components/OrderPaymentPanel.vue'
import OrderStatusBadge from '@/modules/orders/components/OrderStatusBadge.vue'
import OrderTotals from '@/modules/orders/components/OrderTotals.vue'
import { useAvailability } from '@/modules/inventory/composables/useInventory'
import {
  useOrder,
  useQuote,
  useReserveOrder,
  useSubmitOrder,
} from '@/modules/orders/composables/useOrders'
import { useSubmittedNotice } from '@/modules/orders/composables/useSubmittedNotice'
import { formatOrderNumber } from '@/modules/orders/format'
import type { OrderLine } from '@/modules/orders/types'
import { ApiError } from '@/services/http/apiError'
import { formatDateTime } from '@/utils/datetime'
import { formatMoney } from '@/utils/money'

const { id } = defineProps<{ id: string }>()

const { t } = useI18n()
const session = useSessionStore()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const notifySubmitted = useSubmittedNotice()

const { data: order, isPending, error, refetch } = useOrder(() => id)
const notFound = computed(() => error.value instanceof ApiError && error.value.status === 404)

const isDraft = computed(() => order.value?.status === 'DRAFT')
const canEdit = computed(() => isDraft.value && session.can('orders:create'))
// Espelha a política do backend (`permission_to_cancel`): pedido pago só com `orders:cancel_paid`,
// e o cancelamento estorna o pagamento. Aqui é só UX; o backend decide.
const CANCELLABLE = new Set(['DRAFT', 'PENDING', 'AWAITING_PAYMENT'])
const CANCELLABLE_WITH_REFUND = new Set(['PAID', 'PROCESSING', 'READY_TO_SHIP'])
const refundsOnCancel = computed(() => CANCELLABLE_WITH_REFUND.has(order.value?.status ?? ''))
const canCancel = computed(() =>
  refundsOnCancel.value
    ? session.can('orders:cancel_paid')
    : session.can('orders:cancel') && CANCELLABLE.has(order.value?.status ?? ''),
)
const IN_FULFILLMENT = new Set(['PAID', 'PROCESSING', 'READY_TO_SHIP', 'SHIPPED', 'DELIVERED'])
const showFulfillment = computed(() => IN_FULFILLMENT.has(order.value?.status ?? ''))
const showPayments = computed(
  () => order.value?.status === 'AWAITING_PAYMENT' || Boolean(order.value?.payments.length),
)
// Enviado, mas sem reserva (faltou estoque ou a reserva expirou).
const withoutReservation = computed(() => order.value?.status === 'PENDING')
const title = computed(() =>
  order.value
    ? (formatOrderNumber(order.value.number) ?? t('orders.draftTitle'))
    : t('common.loading'),
)

// Rascunho mostra a cotação ATUAL (o valor guardado é a estimativa da última edição): a pessoa
// vê o preço que vai confirmar. Sem `orders:create` (ex.: VIEWER), fica a estimativa guardada.
const draftQuote = useQuote(() =>
  isDraft.value && order.value?.lines.length && session.can('orders:create')
    ? {
        customer_id: order.value.customer.id,
        lines: order.value.lines.map((l) => ({ product_id: l.product_id, quantity: l.quantity })),
      }
    : null,
)
const liveQuote = computed(() =>
  isDraft.value && !draftQuote.error.value ? draftQuote.data.value : undefined,
)
const shown = (line: OrderLine) => {
  const quoted = liveQuote.value?.lines.find((q) => q.product_id === line.product_id)
  return {
    unit_price: quoted?.unit_price ?? line.unit_price,
    line_total: quoted?.line_total ?? line.line_total,
    price_source: quoted?.price_source ?? line.price_source,
  }
}
const totals = computed(() => liveQuote.value ?? order.value)

// Envio do rascunho confirmando o total exibido; se mudou, mostra o novo e pede confirmação.
const submit = useSubmitOrder()
const submitError = ref<string | null>(null)
const changedTotal = ref<string | null>(null)
async function onSubmit(expectedTotal: string) {
  submitError.value = null
  try {
    const submitted = await submit.mutateAsync({ id, expectedTotal })
    changedTotal.value = null
    notifySubmitted(submitted)
  } catch (cause) {
    if (cause instanceof ApiError && cause.code === 'PRICES_CHANGED') {
      changedTotal.value = String(cause.details.actual)
      submitError.value = t('orders.editor.pricesChanged', {
        total: formatMoney(changedTotal.value),
      })
      void draftQuote.refetch()
    } else submitError.value = errorMessage(cause)
  }
}

// Disponível por item para pedidos sem reserva: mostra o que falta antes de tentar de novo.
const stock = useAvailability(
  () => (withoutReservation.value ? (order.value?.warehouse?.id ?? '') : ''),
  () => order.value?.lines.map((line) => line.product_id) ?? [],
)
const availableOf = (line: OrderLine) =>
  stock.data.value?.find((level) => level.product_id === line.product_id)?.available

const reserve = useReserveOrder()
const reserveError = ref<string | null>(null)
const shortages = ref<{ sku: string; requested: number; available: number }[]>([])
async function onReserve() {
  reserveError.value = null
  shortages.value = []
  try {
    const reserved = await reserve.mutateAsync(id)
    toasts.success(
      t('orders.reservation.reserved', { date: formatDateTime(reserved.payment_due_at ?? '') }),
    )
  } catch (cause) {
    reserveError.value = errorMessage(cause)
    if (cause instanceof ApiError && Array.isArray(cause.details.lines)) {
      const lines = cause.details.lines as {
        product_id: string
        requested: number
        available: number
      }[]
      shortages.value = lines.map((short) => ({
        sku: order.value?.lines.find((l) => l.product_id === short.product_id)?.sku ?? '—',
        requested: short.requested,
        available: short.available,
      }))
    }
  }
}

const cancelOpen = ref(false)
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

    <p v-if="isPending" class="text-sm text-text-secondary" role="status">
      {{ t('common.loading') }}
    </p>
    <EmptyState
      v-else-if="notFound"
      :title="t('orders.notFoundTitle')"
      :description="t('orders.notFoundDescription')"
    />
    <div v-else-if="error" class="flex flex-wrap items-center gap-3 text-sm" role="alert">
      <span>{{ errorMessage(error) }}</span>
      <BaseButton size="sm" variant="secondary" @click="refetch()">{{
        t('common.retry')
      }}</BaseButton>
    </div>

    <template v-else-if="order">
      <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-3">
            <h1 class="text-2xl font-semibold tracking-tight">{{ title }}</h1>
            <OrderStatusBadge :status="order.status" />
          </div>
          <p class="mt-1 text-sm text-text-secondary">
            {{
              order.submitted_at
                ? t('orders.submittedAt', { date: formatDateTime(order.submitted_at) })
                : t('orders.createdAt', { date: formatDateTime(order.created_at) })
            }}
          </p>
        </div>
        <div class="flex shrink-0 flex-wrap gap-2">
          <RouterLink
            v-if="canEdit"
            :to="{ name: 'order-edit', params: { id: order.id } }"
            class="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-medium hover:bg-surface-muted"
          >
            <Pencil class="size-4" aria-hidden="true" />
            {{ t('orders.actions.editDraft') }}
          </RouterLink>
          <BaseButton
            v-if="canEdit"
            :loading="submit.isPending.value"
            @click="onSubmit(totals?.total ?? order.total)"
          >
            <Send class="size-4" aria-hidden="true" />
            {{ t('orders.actions.submit') }}
          </BaseButton>
          <BaseButton v-if="canCancel" variant="secondary" @click="cancelOpen = true">
            <XCircle class="size-4" aria-hidden="true" />
            {{ isDraft ? t('orders.actions.discardDraft') : t('orders.actions.cancel') }}
          </BaseButton>
        </div>
      </header>

      <section
        v-if="order.status === 'AWAITING_PAYMENT' && order.payment_due_at"
        class="mb-6 flex items-start gap-3 rounded-lg border border-border bg-surface p-4 text-sm"
      >
        <PackageCheck class="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
        <p>
          {{
            t('orders.reservation.reservedUntil', { date: formatDateTime(order.payment_due_at) })
          }}
        </p>
      </section>

      <section
        v-if="withoutReservation"
        aria-labelledby="reservation-heading"
        class="mb-6 flex flex-col gap-3 rounded-lg border border-warning/50 bg-surface p-4 text-sm"
      >
        <div class="flex items-start gap-3">
          <TriangleAlert class="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
          <div>
            <h2 id="reservation-heading" class="font-semibold">
              {{ t('orders.reservation.missingTitle') }}
            </h2>
            <p class="text-text-secondary">{{ t('orders.reservation.missingDescription') }}</p>
          </div>
        </div>
        <FormAlert :message="reserveError" />
        <ul v-if="shortages.length" class="ml-7 list-disc text-sm">
          <li v-for="short in shortages" :key="short.sku">
            {{ t('orders.reservation.shortage', short) }}
          </li>
        </ul>
        <div v-if="session.can('orders:create')" class="ml-7">
          <BaseButton :loading="reserve.isPending.value" @click="onReserve">
            {{ t('orders.actions.reserve') }}
          </BaseButton>
        </div>
      </section>

      <div v-if="submitError" class="mb-6 flex flex-col gap-3">
        <FormAlert :message="submitError" />
        <div v-if="changedTotal">
          <BaseButton :loading="submit.isPending.value" @click="onSubmit(changedTotal)">
            {{ t('orders.actions.submitWithNewTotal', { total: formatMoney(changedTotal) }) }}
          </BaseButton>
        </div>
      </div>

      <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div class="flex min-w-0 flex-col gap-6">
          <section
            aria-labelledby="order-items-heading"
            class="rounded-lg border border-border bg-surface p-5"
          >
            <h2 id="order-items-heading" class="mb-3 text-base font-semibold">
              {{ t('orders.detail.items', { count: order.lines.length }) }}
            </h2>
            <p v-if="!order.lines.length" class="text-sm text-text-secondary">
              {{ t('orders.detail.noItems') }}
            </p>
            <div v-else class="overflow-x-auto">
              <table class="w-full min-w-[560px] text-sm">
                <caption class="sr-only">
                  {{
                    t('orders.editor.linesCaption')
                  }}
                </caption>
                <thead>
                  <tr class="border-b border-border text-left text-xs text-text-secondary">
                    <th scope="col" class="py-2 pr-3 font-medium">
                      {{ t('orders.fields.product') }}
                    </th>
                    <th scope="col" class="py-2 pr-3 text-right font-medium">
                      {{ t('orders.fields.quantity') }}
                    </th>
                    <th
                      v-if="withoutReservation"
                      scope="col"
                      class="py-2 pr-3 text-right font-medium"
                    >
                      {{ t('orders.fields.available') }}
                    </th>
                    <th scope="col" class="py-2 pr-3 text-right font-medium">
                      {{ t('orders.fields.unitPrice') }}
                    </th>
                    <th scope="col" class="py-2 text-right font-medium">
                      {{ t('orders.fields.lineTotal') }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="line in order.lines" :key="line.id" class="border-b border-border">
                    <td class="py-2 pr-3">
                      <span class="font-mono text-xs text-text-secondary">{{ line.sku }}</span>
                      <span class="ml-2">{{ line.product_name }}</span>
                      <span
                        v-if="shown(line).price_source === 'SEGMENT'"
                        class="ml-2 text-xs text-text-secondary"
                      >
                        {{ t('orders.detail.segmentPrice') }}
                      </span>
                    </td>
                    <td class="py-2 pr-3 text-right tabular-nums">{{ line.quantity }}</td>
                    <td v-if="withoutReservation" class="py-2 pr-3 text-right tabular-nums">
                      <span>{{ availableOf(line) ?? '—' }}</span>
                      <span
                        v-if="(availableOf(line) ?? Infinity) < line.quantity"
                        class="mt-1 flex items-center justify-end gap-1 text-xs text-warning"
                      >
                        <TriangleAlert class="size-3.5" aria-hidden="true" />
                        {{
                          t('orders.reservation.missingUnits', {
                            count: line.quantity - (availableOf(line) ?? 0),
                          })
                        }}
                      </span>
                    </td>
                    <td class="py-2 pr-3 text-right tabular-nums">
                      {{ formatMoney(shown(line).unit_price) }}
                    </td>
                    <td class="py-2 text-right font-medium tabular-nums">
                      {{ formatMoney(shown(line).line_total) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section
            aria-labelledby="order-history-heading"
            class="rounded-lg border border-border bg-surface p-5"
          >
            <h2 id="order-history-heading" class="mb-3 text-base font-semibold">
              {{ t('orders.detail.history') }}
            </h2>
            <ol class="flex flex-col gap-3 border-l border-border pl-4">
              <li v-for="entry in [...order.history].reverse()" :key="entry.id" class="text-sm">
                <p class="font-medium">
                  {{
                    entry.from_status
                      ? t('orders.detail.transition', {
                          from: t(`orders.status.${entry.from_status}`),
                          to: t(`orders.status.${entry.to_status}`),
                        })
                      : t('orders.detail.created', {
                          status: t(`orders.status.${entry.to_status}`),
                        })
                  }}
                </p>
                <p class="text-xs text-text-secondary">
                  {{ formatDateTime(entry.changed_at) }}
                  <template v-if="entry.changed_by"> · {{ entry.changed_by.name }}</template>
                </p>
                <p v-if="entry.reason" class="mt-1 text-text-secondary">“{{ entry.reason }}”</p>
              </li>
            </ol>
          </section>
        </div>

        <aside class="flex h-fit flex-col gap-6">
          <OrderFulfillmentPanel v-if="showFulfillment" :order="order" />
          <OrderPaymentPanel v-if="showPayments" :order="order" />
          <section
            aria-labelledby="order-summary-heading"
            class="rounded-lg border border-border bg-surface p-5"
          >
            <h2 id="order-summary-heading" class="mb-3 text-base font-semibold">
              {{ t('orders.editor.summary') }}
            </h2>
            <OrderTotals
              :subtotal="totals?.subtotal ?? null"
              :discount-total="totals?.discount_total ?? null"
              :shipping-total="totals?.shipping_total ?? null"
              :total="totals?.total ?? null"
              :estimate="isDraft"
            />
            <p
              v-if="isDraft && draftQuote.error.value"
              class="mt-2 text-xs text-danger"
              role="status"
            >
              {{
                t('orders.detail.quoteFailed', { message: errorMessage(draftQuote.error.value) })
              }}
            </p>
          </section>
          <section
            aria-labelledby="order-customer-heading"
            class="rounded-lg border border-border bg-surface p-5 text-sm"
          >
            <h2 id="order-customer-heading" class="mb-3 text-base font-semibold">
              {{ t('orders.detail.customerAndDelivery') }}
            </h2>
            <dl class="flex flex-col gap-3">
              <div>
                <dt class="text-xs text-text-secondary">{{ t('orders.fields.customer') }}</dt>
                <dd>
                  <RouterLink
                    :to="{ name: 'customer-detail', params: { id: order.customer.id } }"
                    class="text-link underline-offset-2 hover:underline"
                  >
                    {{ order.customer.display_name }}
                  </RouterLink>
                  <span class="block text-xs text-text-secondary tabular-nums">
                    {{ order.customer.tax_id_formatted }}
                  </span>
                </dd>
              </div>
              <div v-if="order.purchase_order_number">
                <dt class="text-xs text-text-secondary">
                  {{ t('orders.fields.purchaseOrderNumber') }}
                </dt>
                <dd>{{ order.purchase_order_number }}</dd>
              </div>
              <div>
                <dt class="text-xs text-text-secondary">
                  {{ t('orders.fields.shippingAddress') }}
                </dt>
                <dd v-if="order.shipping">
                  <address class="not-italic">
                    {{ order.shipping.label }}<br />
                    {{ order.shipping.street }}, {{ order.shipping.number
                    }}<template v-if="order.shipping.complement">
                      — {{ order.shipping.complement }}</template
                    ><br />
                    {{ order.shipping.district }} · {{ order.shipping.city }}/{{
                      order.shipping.state
                    }}<br />
                    {{
                      t('customers.addresses.postalCodeLine', {
                        code: formatPostalCode(order.shipping.postal_code),
                      })
                    }}
                  </address>
                  <span v-if="isDraft" class="text-xs text-text-secondary">
                    {{ t('orders.detail.addressCopiedOnSubmit') }}
                  </span>
                </dd>
                <dd v-else class="text-text-secondary">{{ t('orders.detail.noAddress') }}</dd>
              </div>
              <div>
                <dt class="text-xs text-text-secondary">{{ t('orders.fields.warehouse') }}</dt>
                <dd>
                  {{
                    order.warehouse
                      ? `${order.warehouse.code} — ${order.warehouse.name}`
                      : t('orders.detail.noWarehouse')
                  }}
                </dd>
              </div>
              <div v-if="order.notes">
                <dt class="text-xs text-text-secondary">{{ t('orders.fields.notes') }}</dt>
                <dd class="whitespace-pre-line">{{ order.notes }}</dd>
              </div>
              <div v-if="order.created_by">
                <dt class="text-xs text-text-secondary">{{ t('orders.fields.createdBy') }}</dt>
                <dd>{{ order.created_by.name }}</dd>
              </div>
            </dl>
          </section>
        </aside>
      </div>

      <CancelOrderDialog
        v-if="canCancel"
        v-model:open="cancelOpen"
        :order="order"
        :releases-stock="order.status === 'AWAITING_PAYMENT' || refundsOnCancel"
        :refunds="refundsOnCancel"
        :title="
          isDraft
            ? t('orders.cancel.discardTitle')
            : t('orders.cancel.title', { number: formatOrderNumber(order.number) })
        "
      />
    </template>
  </div>
</template>
