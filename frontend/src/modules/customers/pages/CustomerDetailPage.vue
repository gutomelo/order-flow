<script setup lang="ts">
import { ArrowLeft, CircleCheck, CircleSlash, Pencil } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useActivationToggle } from '@/composables/useActivationToggle'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useSessionStore } from '@/modules/auth/stores/session'
import CustomerAddresses from '@/modules/customers/components/CustomerAddresses.vue'
import CustomerContacts from '@/modules/customers/components/CustomerContacts.vue'
import CustomerFormDialog from '@/modules/customers/components/CustomerFormDialog.vue'
import { useCustomer, useSetCustomerActive } from '@/modules/customers/composables/useCustomers'
import type { Customer } from '@/modules/customers/types'
import { ApiError } from '@/services/http/apiError'

const { id } = defineProps<{ id: string }>()

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canUpdate = computed(() => session.can('customers:update'))

const { data: customer, isPending, error, refetch } = useCustomer(() => id)
const notFound = computed(() => error.value instanceof ApiError && error.value.status === 404)

const formOpen = ref(false)
const setActive = useSetCustomerActive()
const toggle = useActivationToggle<Customer>({
  mutate: (input) => setActive.mutateAsync(input),
  successMessage: (c) =>
    t(c.is_active ? 'customers.feedback.deactivated' : 'customers.feedback.activated'),
})
</script>

<template>
  <div>
    <RouterLink
      :to="{ name: 'customers' }"
      class="mb-4 inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
    >
      <ArrowLeft class="size-4" aria-hidden="true" />
      {{ t('customers.detail.back') }}
    </RouterLink>

    <p v-if="isPending" class="text-sm text-text-secondary" role="status">
      {{ t('common.loading') }}
    </p>
    <EmptyState
      v-else-if="notFound"
      :title="t('customers.detail.notFoundTitle')"
      :description="t('customers.detail.notFoundDescription')"
    />
    <div v-else-if="error" class="flex flex-wrap items-center gap-3 text-sm" role="alert">
      <span>{{ errorMessage(error) }}</span>
      <BaseButton size="sm" variant="secondary" @click="refetch()">{{
        t('common.retry')
      }}</BaseButton>
    </div>

    <template v-else-if="customer">
      <header class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-3">
            <h1 class="text-2xl font-semibold tracking-tight">{{ customer.display_name }}</h1>
            <StatusBadge
              :label="customer.is_active ? t('common.status.active') : t('common.status.inactive')"
              :icon="customer.is_active ? CircleCheck : CircleSlash"
              :tone="customer.is_active ? 'success' : 'neutral'"
            />
          </div>
          <dl class="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm">
            <div v-if="customer.trade_name" class="flex gap-1">
              <dt class="text-text-secondary">{{ t('customers.fields.legalName') }}:</dt>
              <dd>{{ customer.legal_name }}</dd>
            </div>
            <div class="flex gap-1">
              <dt class="text-text-secondary">{{ t('customers.fields.taxId') }}:</dt>
              <dd class="tabular-nums">{{ customer.tax_id_formatted }}</dd>
            </div>
            <div class="flex gap-1">
              <dt class="text-text-secondary">{{ t('customers.fields.segment') }}:</dt>
              <dd>
                {{
                  customer.segment
                    ? customer.segment.is_active
                      ? customer.segment.name
                      : t('customers.inactiveName', { name: customer.segment.name })
                    : t('customers.noSegment')
                }}
              </dd>
            </div>
            <div v-if="customer.email" class="flex gap-1">
              <dt class="text-text-secondary">{{ t('customers.fields.email') }}:</dt>
              <dd>{{ customer.email }}</dd>
            </div>
            <div v-if="customer.phone" class="flex gap-1">
              <dt class="text-text-secondary">{{ t('customers.fields.phone') }}:</dt>
              <dd>{{ customer.phone }}</dd>
            </div>
          </dl>
        </div>
        <div v-if="canUpdate" class="flex shrink-0 gap-2">
          <BaseButton variant="secondary" @click="formOpen = true">
            <Pencil class="size-4" aria-hidden="true" />
            {{ t('common.edit') }}
          </BaseButton>
          <BaseButton variant="secondary" @click="toggle.ask(customer)">
            <component
              :is="customer.is_active ? CircleSlash : CircleCheck"
              class="size-4"
              aria-hidden="true"
            />
            {{ customer.is_active ? t('common.deactivate') : t('common.activate') }}
          </BaseButton>
        </div>
      </header>

      <div class="flex flex-col gap-6">
        <CustomerAddresses :customer-id="customer.id" :can-edit="canUpdate" />
        <CustomerContacts :customer-id="customer.id" :can-edit="canUpdate" />
      </div>

      <CustomerFormDialog
        v-if="canUpdate"
        :key="customer.updated_at"
        v-model:open="formOpen"
        :customer="customer"
      />
      <ConfirmDialog
        v-model:open="toggle.open.value"
        :title="
          customer.is_active
            ? t('common.confirmDeactivateTitle', { name: customer.display_name })
            : t('common.confirmActivateTitle', { name: customer.display_name })
        "
        :description="
          customer.is_active
            ? t('customers.confirm.deactivateDescription')
            : t('customers.confirm.activateDescription')
        "
        :confirm-label="customer.is_active ? t('common.deactivate') : t('common.activate')"
        :tone="customer.is_active ? 'danger' : 'primary'"
        :loading="toggle.running.value"
        :error="toggle.error.value"
        @confirm="toggle.confirm"
      />
    </template>
  </div>
</template>
