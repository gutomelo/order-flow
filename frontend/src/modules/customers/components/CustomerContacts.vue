<script setup lang="ts">
import { Pencil, Plus, Star, Trash2, UserRound } from '@lucide/vue'
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import ContactFormDialog from '@/modules/customers/components/ContactFormDialog.vue'
import {
  useContacts,
  useRemoveContact,
  useSetPrimaryContact,
} from '@/modules/customers/composables/useCustomers'
import type { CustomerContact } from '@/modules/customers/types'

const { customerId, canEdit } = defineProps<{ customerId: string; canEdit: boolean }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const { data, isPending, error, refetch } = useContacts(() => customerId)

const formOpen = ref(false)
const editing = ref<CustomerContact | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')
function openForm(contact: CustomerContact | null) {
  editing.value = contact
  formOpen.value = true
}

// Mesmo cuidado de foco de CustomerAddresses: o botão clicado deixa de existir.
async function focusAfterUpdate(elementId: string) {
  await nextTick()
  await nextTick()
  document.getElementById(elementId)?.focus()
}

const setPrimary = useSetPrimaryContact(customerId)
async function makePrimary(contact: CustomerContact) {
  try {
    await setPrimary.mutateAsync(contact.id)
    toasts.success(t('customers.contacts.feedback.primary', { name: contact.name }))
    await focusAfterUpdate(`contact-${contact.id}`)
  } catch (cause) {
    toasts.error(errorMessage(cause))
  }
}

const remove = useRemoveContact(customerId)
const removing = ref<CustomerContact | null>(null)
const removeError = ref<string | null>(null)
const removeOpen = computed({
  get: () => removing.value !== null,
  set: (isOpen) => {
    if (!isOpen) removing.value = null
  },
})
function askRemove(contact: CustomerContact) {
  removeError.value = null
  removing.value = contact
}
async function confirmRemove() {
  const contact = removing.value
  if (!contact) return
  try {
    await remove.mutateAsync(contact.id)
    toasts.success(t('customers.contacts.feedback.removed', { name: contact.name }))
    removing.value = null
    await focusAfterUpdate('contacts-heading')
  } catch (cause) {
    removeError.value = errorMessage(cause)
  }
}
</script>

<template>
  <section
    aria-labelledby="contacts-heading"
    class="rounded-lg border border-border bg-surface p-5"
  >
    <header class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 id="contacts-heading" tabindex="-1" class="text-base font-semibold focus:outline-none">
          {{ t('customers.contacts.title') }}
        </h2>
        <p class="text-sm text-text-secondary">{{ t('customers.contacts.description') }}</p>
      </div>
      <BaseButton v-if="canEdit" size="sm" variant="secondary" @click="openForm(null)">
        <Plus class="size-4" aria-hidden="true" />
        {{ t('customers.contacts.create') }}
      </BaseButton>
    </header>

    <p v-if="isPending" class="text-sm text-text-secondary" role="status">
      {{ t('common.loading') }}
    </p>
    <div v-else-if="error" class="flex flex-wrap items-center gap-3 text-sm" role="alert">
      <span>{{ t('customers.contacts.error', { message: errorMessage(error) }) }}</span>
      <BaseButton size="sm" variant="secondary" @click="refetch()">{{
        t('common.retry')
      }}</BaseButton>
    </div>
    <div
      v-else-if="!data?.length"
      class="flex items-start gap-3 rounded-md border border-dashed border-border p-4 text-sm"
    >
      <UserRound class="mt-0.5 size-4 shrink-0 text-text-secondary" aria-hidden="true" />
      <p class="text-text-secondary">{{ t('customers.contacts.empty') }}</p>
    </div>
    <ul v-else class="divide-y divide-border">
      <li
        v-for="contact in data"
        :key="contact.id"
        class="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
      >
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h3 :id="`contact-${contact.id}`" tabindex="-1" class="font-medium focus:outline-none">
              {{ contact.name }}
            </h3>
            <StatusBadge
              v-if="contact.is_primary"
              :label="t('customers.contacts.primary')"
              :icon="Star"
              tone="info"
            />
          </div>
          <p v-if="contact.job_title" class="text-sm text-text-secondary">
            {{ contact.job_title }}
          </p>
          <p class="text-sm">
            <a
              v-if="contact.email"
              :href="`mailto:${contact.email}`"
              class="text-link underline-offset-2 hover:underline"
              >{{ contact.email }}</a
            >
            <span
              v-if="contact.email && contact.phone"
              class="text-text-secondary"
              aria-hidden="true"
            >
              ·
            </span>
            <span v-if="contact.phone">{{ contact.phone }}</span>
          </p>
        </div>
        <div v-if="canEdit" class="flex flex-wrap gap-1">
          <BaseButton
            v-if="!contact.is_primary"
            variant="ghost"
            size="sm"
            :disabled="setPrimary.isPending.value"
            @click="makePrimary(contact)"
          >
            <span aria-hidden="true">{{ t('customers.contacts.makePrimary') }}</span>
            <span class="sr-only">{{
              t('customers.contacts.makePrimaryItem', { name: contact.name })
            }}</span>
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="openForm(contact)">
            <Pencil class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('common.editItem', { name: contact.name }) }}</span>
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="askRemove(contact)">
            <Trash2 class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('common.removeItem', { name: contact.name }) }}</span>
          </BaseButton>
        </div>
      </li>
    </ul>

    <ContactFormDialog
      v-if="canEdit"
      :key="formKey"
      v-model:open="formOpen"
      :customer-id="customerId"
      :contact="editing"
    />
    <ConfirmDialog
      v-model:open="removeOpen"
      :title="t('customers.contacts.confirmRemoveTitle', { name: removing?.name })"
      :description="
        removing?.is_primary
          ? t('customers.contacts.confirmRemovePrimary')
          : t('customers.contacts.confirmRemove')
      "
      :confirm-label="t('common.remove')"
      :loading="remove.isPending.value"
      :error="removeError"
      @confirm="confirmRemove"
    />
  </section>
</template>
