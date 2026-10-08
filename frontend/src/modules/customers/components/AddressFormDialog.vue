<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { BRAZILIAN_STATES, formatPostalCode } from '@/modules/customers/addresses'
import { useSaveAddress } from '@/modules/customers/composables/useCustomers'
import { addressSchema } from '@/modules/customers/schemas/customerForms'
import type { CustomerAddress } from '@/modules/customers/types'

const open = defineModel<boolean>('open', { required: true })
const {
  customerId,
  address = null,
  first = false,
} = defineProps<{
  customerId: string
  address?: CustomerAddress | null
  /** Primeiro endereço do cliente: recebe os dois papéis (regra AD3). */
  first?: boolean
}>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSaveAddress(customerId)

const isEdit = computed(() => address !== null)
const initialValues = {
  label: address?.label ?? '',
  postal_code: address ? formatPostalCode(address.postal_code) : '',
  street: address?.street ?? '',
  number: address?.number ?? '',
  complement: address?.complement ?? '',
  district: address?.district ?? '',
  city: address?.city ?? '',
  state: address?.state ?? '',
}
const form = useZodForm(addressSchema, initialValues)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

const stateOptions = computed(() => [
  { value: '', label: t('customers.addresses.chooseState') },
  ...BRAZILIAN_STATES.map((uf) => ({ value: uf, label: `${uf} — ${t(`customers.states.${uf}`)}` })),
])

async function onSubmit() {
  const saved = await form.submit(
    (data) => save.mutateAsync({ id: address?.id, data }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(
      t(
        isEdit.value
          ? 'customers.addresses.feedback.updated'
          : 'customers.addresses.feedback.created',
      ),
    )
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('customers.addresses.editTitle') : t('customers.addresses.createTitle')"
    :description="first && !isEdit ? t('customers.addresses.createDescription') : undefined"
  >
    <form id="address-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />
      <div class="grid gap-4 sm:grid-cols-[2fr_1fr]">
        <TextField
          v-model="form.values.label"
          :label="t('customers.addresses.fields.label')"
          required
          :help="t('customers.addresses.labelHelp')"
          :error="form.errors.value.label"
        />
        <TextField
          v-model="form.values.postal_code"
          :label="t('customers.addresses.fields.postalCode')"
          required
          inputmode="numeric"
          autocomplete="postal-code"
          :error="form.errors.value.postal_code"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-[3fr_1fr]">
        <TextField
          v-model="form.values.street"
          :label="t('customers.addresses.fields.street')"
          required
          autocomplete="address-line1"
          :error="form.errors.value.street"
        />
        <TextField
          v-model="form.values.number"
          :label="t('customers.addresses.fields.number')"
          required
          :error="form.errors.value.number"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.complement"
          :label="t('customers.addresses.fields.complement')"
          autocomplete="address-line2"
          :error="form.errors.value.complement"
        />
        <TextField
          v-model="form.values.district"
          :label="t('customers.addresses.fields.district')"
          required
          :error="form.errors.value.district"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-[2fr_1fr]">
        <TextField
          v-model="form.values.city"
          :label="t('customers.addresses.fields.city')"
          required
          autocomplete="address-level2"
          :error="form.errors.value.city"
        />
        <SelectField
          v-model="form.values.state"
          :label="t('customers.addresses.fields.state')"
          :options="stateOptions"
          required
          :error="form.errors.value.state"
        />
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="address-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
