<script setup lang="ts">
import { MapPin, Pencil, Plus, Receipt, Trash2, Truck } from '@lucide/vue'
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { formatPostalCode } from '@/modules/customers/addresses'
import AddressFormDialog from '@/modules/customers/components/AddressFormDialog.vue'
import {
  useAddresses,
  useRemoveAddress,
  useSetAddressRole,
} from '@/modules/customers/composables/useCustomers'
import type { AddressRole, CustomerAddress } from '@/modules/customers/types'

const { customerId, canEdit } = defineProps<{ customerId: string; canEdit: boolean }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const { data, isPending, error, refetch } = useAddresses(() => customerId)

const formOpen = ref(false)
const editing = ref<CustomerAddress | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')
function openForm(address: CustomerAddress | null) {
  editing.value = address
  formOpen.value = true
}

// O botão clicado some (o papel mudou ou o item foi removido): o foco iria para o <body>.
// Ele passa para o cartão afetado ou para o título da seção.
async function focusAfterUpdate(elementId: string) {
  await nextTick()
  await nextTick() // o diálogo de confirmação fecha no ciclo seguinte e devolve o foco
  document.getElementById(elementId)?.focus()
}

const setRole = useSetAddressRole(customerId)
async function moveRole(address: CustomerAddress, role: AddressRole) {
  try {
    await setRole.mutateAsync({ id: address.id, role })
    toasts.success(t(`customers.addresses.feedback.${role}`, { label: address.label }))
    await focusAfterUpdate(`address-${address.id}`)
  } catch (cause) {
    toasts.error(errorMessage(cause))
  }
}

const remove = useRemoveAddress(customerId)
const removing = ref<CustomerAddress | null>(null)
const removeError = ref<string | null>(null)
const removeOpen = computed({
  get: () => removing.value !== null,
  set: (isOpen) => {
    if (!isOpen) removing.value = null
  },
})
function askRemove(address: CustomerAddress) {
  removeError.value = null
  removing.value = address
}
async function confirmRemove() {
  const address = removing.value
  if (!address) return
  try {
    await remove.mutateAsync(address.id)
    toasts.success(t('customers.addresses.feedback.removed', { label: address.label }))
    removing.value = null
    await focusAfterUpdate('addresses-heading')
  } catch (cause) {
    removeError.value = errorMessage(cause)
  }
}
</script>

<template>
  <section
    aria-labelledby="addresses-heading"
    class="rounded-lg border border-border bg-surface p-5"
  >
    <header class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 id="addresses-heading" tabindex="-1" class="text-base font-semibold focus:outline-none">
          {{ t('customers.addresses.title') }}
        </h2>
        <p class="text-sm text-text-secondary">{{ t('customers.addresses.description') }}</p>
      </div>
      <BaseButton v-if="canEdit" size="sm" variant="secondary" @click="openForm(null)">
        <Plus class="size-4" aria-hidden="true" />
        {{ t('customers.addresses.create') }}
      </BaseButton>
    </header>

    <p v-if="isPending" class="text-sm text-text-secondary" role="status">
      {{ t('common.loading') }}
    </p>
    <div v-else-if="error" class="flex flex-wrap items-center gap-3 text-sm" role="alert">
      <span>{{ t('customers.addresses.error', { message: errorMessage(error) }) }}</span>
      <BaseButton size="sm" variant="secondary" @click="refetch()">{{
        t('common.retry')
      }}</BaseButton>
    </div>
    <div
      v-else-if="!data?.length"
      class="flex items-start gap-3 rounded-md border border-dashed border-border p-4 text-sm"
    >
      <MapPin class="mt-0.5 size-4 shrink-0 text-text-secondary" aria-hidden="true" />
      <p class="text-text-secondary">{{ t('customers.addresses.empty') }}</p>
    </div>
    <ul v-else class="grid gap-3 md:grid-cols-2">
      <li v-for="address in data" :key="address.id">
        <article class="flex h-full flex-col gap-3 rounded-md border border-border p-4">
          <div class="flex flex-wrap items-center gap-2">
            <h3 :id="`address-${address.id}`" tabindex="-1" class="font-medium focus:outline-none">
              {{ address.label }}
            </h3>
            <StatusBadge
              v-if="address.is_billing"
              :label="t('customers.addresses.roles.billing')"
              :icon="Receipt"
              tone="info"
            />
            <StatusBadge
              v-if="address.is_default_shipping"
              :label="t('customers.addresses.roles.defaultShipping')"
              :icon="Truck"
              tone="success"
            />
          </div>
          <address class="text-sm not-italic text-text-secondary">
            {{ address.street }}, {{ address.number
            }}<template v-if="address.complement"> — {{ address.complement }}</template
            ><br />
            {{ address.district }} · {{ address.city }}/{{ address.state }}<br />
            {{
              t('customers.addresses.postalCodeLine', {
                code: formatPostalCode(address.postal_code),
              })
            }}
          </address>
          <div v-if="canEdit" class="mt-auto flex flex-wrap gap-1">
            <BaseButton variant="ghost" size="sm" @click="openForm(address)">
              <Pencil class="size-4" aria-hidden="true" />
              {{ t('common.edit') }}
              <span class="sr-only">{{ address.label }}</span>
            </BaseButton>
            <BaseButton
              v-if="!address.is_billing"
              variant="ghost"
              size="sm"
              :disabled="setRole.isPending.value"
              @click="moveRole(address, 'billing')"
            >
              <span aria-hidden="true">{{ t('customers.addresses.makeBilling') }}</span>
              <span class="sr-only">{{
                t('customers.addresses.makeBillingItem', { label: address.label })
              }}</span>
            </BaseButton>
            <BaseButton
              v-if="!address.is_default_shipping"
              variant="ghost"
              size="sm"
              :disabled="setRole.isPending.value"
              @click="moveRole(address, 'default-shipping')"
            >
              <span aria-hidden="true">{{ t('customers.addresses.makeDefaultShipping') }}</span>
              <span class="sr-only">{{
                t('customers.addresses.makeDefaultShippingItem', { label: address.label })
              }}</span>
            </BaseButton>
            <BaseButton variant="ghost" size="sm" @click="askRemove(address)">
              <Trash2 class="size-4" aria-hidden="true" />
              {{ t('common.remove') }}
              <span class="sr-only">{{ address.label }}</span>
            </BaseButton>
          </div>
        </article>
      </li>
    </ul>

    <AddressFormDialog
      v-if="canEdit"
      :key="formKey"
      v-model:open="formOpen"
      :customer-id="customerId"
      :address="editing"
      :first="!data?.length"
    />
    <ConfirmDialog
      v-model:open="removeOpen"
      :title="t('customers.addresses.confirmRemoveTitle', { label: removing?.label })"
      :description="
        removing?.is_billing || removing?.is_default_shipping
          ? t('customers.addresses.confirmRemoveWithRole')
          : t('customers.addresses.confirmRemove')
      "
      :confirm-label="t('common.remove')"
      :loading="remove.isPending.value"
      :error="removeError"
      @confirm="confirmRemove"
    />
  </section>
</template>
