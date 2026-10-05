<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSaveContact } from '@/modules/customers/composables/useCustomers'
import { contactSchema } from '@/modules/customers/schemas/customerForms'
import type { CustomerContact } from '@/modules/customers/types'

const open = defineModel<boolean>('open', { required: true })
const { customerId, contact = null } = defineProps<{
  customerId: string
  contact?: CustomerContact | null
}>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSaveContact(customerId)

const isEdit = computed(() => contact !== null)
const initialValues = {
  name: contact?.name ?? '',
  job_title: contact?.job_title ?? '',
  email: contact?.email ?? '',
  phone: contact?.phone ?? '',
}
const form = useZodForm(contactSchema, initialValues)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

async function onSubmit() {
  const saved = await form.submit(
    (data) => save.mutateAsync({ id: contact?.id, data }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(
      t(
        isEdit.value
          ? 'customers.contacts.feedback.updated'
          : 'customers.contacts.feedback.created',
      ),
    )
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('customers.contacts.editTitle') : t('customers.contacts.createTitle')"
  >
    <form id="contact-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />
      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.name"
          :label="t('customers.contacts.fields.name')"
          required
          autocomplete="off"
          :error="form.errors.value.name"
        />
        <TextField
          v-model="form.values.job_title"
          :label="t('customers.contacts.fields.jobTitle')"
          :help="t('customers.contacts.jobTitleHelp')"
          :error="form.errors.value.job_title"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.email"
          type="email"
          autocomplete="off"
          :label="t('customers.contacts.fields.email')"
          :help="t('customers.contacts.channelHelp')"
          :error="form.errors.value.email"
        />
        <TextField
          v-model="form.values.phone"
          autocomplete="off"
          :label="t('customers.contacts.fields.phone')"
          :error="form.errors.value.phone"
        />
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="contact-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
