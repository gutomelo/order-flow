<script setup lang="ts">
import { RotateCcw, Undo2, Wallet } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectField from '@/components/ui/SelectField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useIdempotencyKey } from '@/composables/useIdempotencyKey'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useSessionStore } from '@/modules/auth/stores/session'
import type { PaymentStatus } from '@/modules/orders/types'
import { PAYMENTS_PAGE_SIZE } from '@/modules/payments/api/paymentsApi'
import PaymentStatusBadge from '@/modules/payments/components/PaymentStatusBadge.vue'
import {
  useConfirmRefund,
  usePaymentsList,
  useRetryRefund,
} from '@/modules/payments/composables/usePayments'
import { useProviderReason } from '@/modules/payments/composables/useProviderReason'
import type { Payment, PaymentFilters } from '@/modules/payments/types'
import { ApiError } from '@/services/http/apiError'
import { formatDateTime } from '@/utils/datetime'
import { formatMoney } from '@/utils/money'

const STATUSES: PaymentStatus[] = ['PENDING', 'APPROVED', 'DECLINED', 'FAILED', 'REFUNDED']

const { t } = useI18n()
const session = useSessionStore()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const reason = useProviderReason()
const canRefund = computed(() => session.can('payments:refund'))

const { filters, field, hasActiveFilters } = useUrlFilters<PaymentFilters>(
  { page: 1, search: '', status: '' },
  {
    status: (raw) => (STATUSES.includes(raw as PaymentStatus) ? (raw as PaymentStatus) : undefined),
  },
)
const search = field('search')
const status = field('status')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = usePaymentsList(filters)

const statusOptions = computed(() => [
  { value: '', label: t('common.allStatuses') },
  ...STATUSES.map((value) => ({ value, label: t(`payments.paymentStatus.${value}`) })),
])
const columns = computed(() => [
  { key: 'order', label: t('payments.fields.order') },
  { key: 'method', label: t('payments.fields.method') },
  { key: 'status', label: t('common.status.label') },
  { key: 'amount', label: t('payments.fields.amount'), align: 'right' as const },
  { key: 'refunds', label: t('payments.fields.refund') },
  { key: 'date', label: t('payments.fields.date') },
])

type Refund = Payment['refunds'][number]

/** Ação pendente de confirmação: nova tentativa no provedor ou estorno feito fora do sistema. */
const pending = ref<{ action: 'retry' | 'confirm'; refund: Refund; payment: Payment } | null>(null)
const confirmOpen = ref(false)
const actionError = ref<string | null>(null)
const attempt = ref(0)
const actionKey = useIdempotencyKey(() => [
  pending.value?.action,
  pending.value?.refund.id,
  attempt.value,
])
const retry = useRetryRefund()
const confirmManual = useConfirmRefund()
const running = computed(() => retry.isPending.value || confirmManual.isPending.value)

function ask(action: 'retry' | 'confirm', payment: Payment, refund: Refund) {
  pending.value = { action, refund, payment }
  actionError.value = null
  confirmOpen.value = true
}

async function onConfirm() {
  if (!pending.value) return
  const { action, refund } = pending.value
  actionError.value = null
  try {
    if (action === 'retry') await retry.mutateAsync({ id: refund.id, key: actionKey() })
    else await confirmManual.mutateAsync({ id: refund.id, key: actionKey() })
    attempt.value++
    toasts.success(t(`payments.refundActions.${action}Done`))
    confirmOpen.value = false
  } catch (cause) {
    if (cause instanceof ApiError && cause.status !== null) attempt.value++
    actionError.value = errorMessage(cause)
  }
}
</script>

<template>
  <div>
    <PageHeader :title="t('payments.title')" :description="t('payments.description')" />

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('payments.filters.search')" />
      <SelectField
        v-model="status"
        :label="t('common.status.label')"
        :options="statusOptions"
        hide-label
      />
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('payments.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="PAYMENTS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('payments.error.title')"
      :empty-title="t('payments.empty.title')"
      :empty-description="t('payments.empty.description')"
      :empty-icon="Wallet"
      :filtered="hasActiveFilters"
      @retry="refetch()"
    >
      <template #cell-order="{ row }">
        <RouterLink
          :to="{ name: 'order-detail', params: { id: row.order_id } }"
          class="font-medium text-link tabular-nums underline-offset-2 hover:underline"
        >
          {{ row.order_reference }}
        </RouterLink>
      </template>
      <template #cell-method="{ row }">
        <p>{{ t(`payments.method.${row.method}`) }}</p>
        <p v-if="row.manual_reference" class="text-xs text-text-secondary">
          {{ t('payments.referenceLine', { reference: row.manual_reference }) }}
        </p>
        <p v-if="row.decline_reason" class="text-xs text-text-secondary">
          {{ t('payments.declineLine', { reason: reason(row.decline_reason) }) }}
        </p>
      </template>
      <template #cell-status="{ row }">
        <PaymentStatusBadge kind="payment" :status="row.status" />
      </template>
      <template #cell-amount="{ row }">
        <span class="tabular-nums">{{ formatMoney(row.amount) }}</span>
      </template>
      <template #cell-refunds="{ row }">
        <span v-if="!row.refunds.length" class="text-text-secondary">—</span>
        <div v-for="refund in row.refunds" :key="refund.id" class="flex flex-col items-start gap-1">
          <PaymentStatusBadge kind="refund" :status="refund.status" />
          <span v-if="refund.failure_reason" class="text-xs text-text-secondary">
            {{ reason(refund.failure_reason) }}
          </span>
          <BaseButton
            v-if="canRefund && row.method === 'CARD' && refund.status === 'FAILED'"
            size="sm"
            variant="secondary"
            @click="ask('retry', row, refund)"
          >
            <RotateCcw class="size-4" aria-hidden="true" />
            {{ t('payments.refundActions.retry') }}
          </BaseButton>
          <BaseButton
            v-if="canRefund && row.method === 'MANUAL' && refund.status === 'PENDING'"
            size="sm"
            variant="secondary"
            @click="ask('confirm', row, refund)"
          >
            <Undo2 class="size-4" aria-hidden="true" />
            {{ t('payments.refundActions.confirm') }}
          </BaseButton>
        </div>
      </template>
      <template #cell-date="{ row }">
        <span class="text-text-secondary">{{ formatDateTime(row.created_at) }}</span>
      </template>
    </DataTable>

    <ConfirmDialog
      v-model:open="confirmOpen"
      tone="primary"
      :title="
        t(`payments.refundActions.${pending?.action ?? 'retry'}Title`, {
          order: pending?.payment.order_reference,
        })
      "
      :description="
        t(`payments.refundActions.${pending?.action ?? 'retry'}Description`, {
          amount: formatMoney(pending?.payment.amount ?? '0'),
        })
      "
      :confirm-label="t(`payments.refundActions.${pending?.action ?? 'retry'}`)"
      :loading="running"
      :error="actionError"
      @confirm="onConfirm"
    />
  </div>
</template>
