<script setup lang="ts">
import { CreditCard, Hourglass, Landmark } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useIdempotencyKey } from '@/composables/useIdempotencyKey'
import { useSessionStore } from '@/modules/auth/stores/session'
import { usePayOrder, useRecordPayment } from '@/modules/orders/composables/useOrders'
import type { Order } from '@/modules/orders/types'
import PaymentStatusBadge from '@/modules/payments/components/PaymentStatusBadge.vue'
import { useProviderReason } from '@/modules/payments/composables/useProviderReason'
import { ApiError } from '@/services/http/apiError'
import { formatDateTime } from '@/utils/datetime'
import { formatMoney } from '@/utils/money'

/**
 * Pagamento do pedido. Em produção o token viria do widget do provedor (o OrderFlow nunca vê o
 * cartão); com o gateway simulado, a pessoa escolhe o cenário de teste (docs/domain/payments.md).
 */
const TEST_CARDS = [
  'tok_approved',
  'tok_declined',
  'tok_timeout',
  'tok_unavailable',
  'tok_refund_fails',
]

const { order } = defineProps<{ order: Order }>()

const { t } = useI18n()
const session = useSessionStore()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const reason = useProviderReason()

const awaiting = computed(() => order.status === 'AWAITING_PAYMENT')
const inFlight = computed(() => order.payments.some((p) => p.status === 'PENDING'))
const canPay = computed(() => awaiting.value && session.can('payments:create'))

// Chave por intenção (ADR-012): repetir após falha de rede reaproveita a chave; depois de uma
// resposta do servidor (aprovado, recusado...), nova tentativa é outra intenção.
const cardToken = ref(TEST_CARDS[0] ?? '')
const cardAttempt = ref(0)
const cardKey = useIdempotencyKey(() => [order.id, cardToken.value, cardAttempt.value])
const pay = usePayOrder()
const payError = ref<string | null>(null)

async function onPay() {
  payError.value = null
  try {
    const { accepted } = await pay.mutateAsync({
      id: order.id,
      cardToken: cardToken.value,
      key: cardKey(),
    })
    cardAttempt.value++
    if (accepted) toasts.warning(t('orders.payment.processing'))
    else toasts.success(t('orders.payment.approved'))
  } catch (cause) {
    if (cause instanceof ApiError && cause.status !== null) cardAttempt.value++
    payError.value = errorMessage(cause)
  }
}

const reference = ref('')
const referenceError = ref('')
const manualAttempt = ref(0)
const manualKey = useIdempotencyKey(() => [order.id, reference.value.trim(), manualAttempt.value])
const record = useRecordPayment()
const recordError = ref<string | null>(null)

async function onRecord() {
  recordError.value = null
  referenceError.value = reference.value.trim() ? '' : t('orders.payment.referenceRequired')
  if (referenceError.value) {
    document.getElementById('manual-reference')?.querySelector('input')?.focus()
    return
  }
  try {
    await record.mutateAsync({ id: order.id, reference: reference.value.trim(), key: manualKey() })
    manualAttempt.value++
    reference.value = ''
    toasts.success(t('orders.payment.recorded'))
  } catch (cause) {
    if (cause instanceof ApiError && cause.status !== null) manualAttempt.value++
    if (cause instanceof ApiError && cause.details.field === 'reference')
      referenceError.value = cause.message
    else recordError.value = errorMessage(cause)
  }
}

const cardOptions = computed(() =>
  TEST_CARDS.map((value) => ({ value, label: t(`orders.payment.testCards.${value}`) })),
)
</script>

<template>
  <section
    aria-labelledby="order-payment-heading"
    class="rounded-lg border border-border bg-surface p-5 text-sm"
  >
    <h2 id="order-payment-heading" class="mb-3 text-base font-semibold">
      {{ t('orders.payment.title') }}
    </h2>

    <p v-if="inFlight" class="mb-4 flex items-start gap-2" role="status">
      <Hourglass class="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
      {{ t('orders.payment.inFlight') }}
    </p>

    <div v-if="canPay && !inFlight" class="mb-4 flex flex-col gap-5">
      <form class="flex flex-col gap-3" novalidate @submit.prevent="onPay">
        <FormAlert :message="payError" />
        <SelectField
          v-model="cardToken"
          :label="t('orders.payment.testCard')"
          :help="t('orders.payment.testCardHelp')"
          :options="cardOptions"
        />
        <div>
          <BaseButton type="submit" :loading="pay.isPending.value">
            <CreditCard class="size-4" aria-hidden="true" />
            {{ t('orders.payment.payWithCard', { total: formatMoney(order.total) }) }}
          </BaseButton>
        </div>
      </form>

      <form
        class="flex flex-col gap-3 border-t border-border pt-4"
        novalidate
        @submit.prevent="onRecord"
      >
        <h3 class="font-medium">{{ t('orders.payment.manualTitle') }}</h3>
        <FormAlert :message="recordError" />
        <div id="manual-reference">
          <TextField
            v-model="reference"
            :label="t('orders.payment.reference')"
            :help="t('orders.payment.referenceHelp')"
            :error="referenceError"
            required
          />
        </div>
        <div>
          <BaseButton type="submit" variant="secondary" :loading="record.isPending.value">
            <Landmark class="size-4" aria-hidden="true" />
            {{ t('orders.payment.record') }}
          </BaseButton>
        </div>
      </form>
    </div>
    <p v-else-if="awaiting && !inFlight" class="mb-4 text-text-secondary">
      {{ t('orders.payment.awaiting') }}
    </p>

    <p v-if="!order.payments.length" class="text-text-secondary">
      {{ t('orders.payment.none') }}
    </p>
    <ul v-else class="flex flex-col gap-3" :aria-label="t('orders.payment.attempts')">
      <li
        v-for="payment in order.payments"
        :key="payment.id"
        class="rounded-md border border-border p-3"
      >
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="font-medium">{{ t(`payments.method.${payment.method}`) }}</span>
          <PaymentStatusBadge kind="payment" :status="payment.status" />
        </div>
        <p class="mt-1 text-xs text-text-secondary">
          <span class="tabular-nums">{{ formatMoney(payment.amount) }}</span>
          · {{ formatDateTime(payment.created_at) }}
        </p>
        <p v-if="payment.manual_reference" class="mt-1 text-xs text-text-secondary">
          {{ t('payments.referenceLine', { reference: payment.manual_reference }) }}
        </p>
        <p v-if="payment.status === 'FAILED'" class="mt-1 text-xs">
          {{ t('payments.failedNote') }}
        </p>
        <p v-if="payment.decline_reason" class="mt-1 text-xs">
          {{ t('payments.declineLine', { reason: reason(payment.decline_reason) }) }}
        </p>
        <ul
          v-if="payment.refunds.length"
          class="mt-2 flex flex-col gap-1 border-t border-border pt-2"
        >
          <li
            v-for="refund in payment.refunds"
            :key="refund.id"
            class="flex flex-wrap items-center justify-between gap-2 text-xs"
          >
            <span>{{ t('payments.refundOn', { date: formatDateTime(refund.created_at) }) }}</span>
            <PaymentStatusBadge kind="refund" :status="refund.status" />
            <span v-if="refund.failure_reason" class="w-full text-text-secondary">
              {{ reason(refund.failure_reason) }}
            </span>
            <span
              v-if="payment.method === 'MANUAL' && refund.status === 'PENDING'"
              class="w-full text-text-secondary"
            >
              {{ t('payments.manualRefundPending') }}
            </span>
          </li>
        </ul>
      </li>
    </ul>
  </section>
</template>
