<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSaveCustomer, useSegmentOptions } from '@/modules/customers/composables/useCustomers'
import { customerSchema } from '@/modules/customers/schemas/customerForms'
import type { Customer } from '@/modules/customers/types'

/** Sem `customer`: criação (e depois vai para o detalhe); com `customer`: edição. */
const open = defineModel<boolean>('open', { required: true })
const { customer = null } = defineProps<{ customer?: Customer | null }>()

const { t } = useI18n()
const router = useRouter()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSaveCustomer()
const segments = useSegmentOptions()

const isEdit = computed(() => customer !== null)
const initialValues = {
  legal_name: customer?.legal_name ?? '',
  trade_name: customer?.trade_name ?? '',
  tax_id: customer?.tax_id_formatted ?? '',
  email: customer?.email ?? '',
  phone: customer?.phone ?? '',
  segment_id: customer?.segment?.id ?? '',
}
const form = useZodForm(customerSchema, initialValues)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

// Segmentos ativos; o segmento atual continua na lista mesmo inativo, para não ser trocado
// sem querer ao salvar outros campos (o backend só valida o segmento quando ele muda).
const segmentOptions = computed(() => [
  { value: '', label: t('customers.form.noSegment') },
  ...(segments.data.value ?? [])
    .filter((s) => s.is_active || s.id === customer?.segment?.id)
    .map((s) => ({
      value: s.id,
      label: s.is_active ? s.name : t('customers.inactiveName', { name: s.name }),
    })),
])

async function onSubmit() {
  let createdId: string | null = null
  const saved = await form.submit(
    async (data) => {
      const result = await save.mutateAsync({ id: customer?.id, data })
      createdId = isEdit.value ? null : result.id
    },
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (!saved) return
  open.value = false
  if (createdId) {
    toasts.success(t('customers.feedback.createdNext'))
    await router.push({ name: 'customer-detail', params: { id: createdId } })
  } else {
    toasts.success(t('customers.feedback.updated'))
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('customers.form.editTitle') : t('customers.form.createTitle')"
  >
    <form id="customer-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />
      <TextField
        v-model="form.values.legal_name"
        :label="t('customers.fields.legalName')"
        required
        :error="form.errors.value.legal_name"
      />
      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.trade_name"
          :label="t('customers.fields.tradeName')"
          :error="form.errors.value.trade_name"
        />
        <TextField
          v-model="form.values.tax_id"
          :label="t('customers.fields.taxId')"
          required
          :help="t('customers.form.taxIdHelp')"
          :error="form.errors.value.tax_id"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.email"
          type="email"
          :label="t('customers.fields.email')"
          :error="form.errors.value.email"
        />
        <TextField
          v-model="form.values.phone"
          :label="t('customers.fields.phone')"
          autocomplete="off"
          :error="form.errors.value.phone"
        />
      </div>
      <SelectField
        v-model="form.values.segment_id"
        :label="t('customers.fields.segment')"
        :options="segmentOptions"
        :help="t('customers.form.segmentHelp')"
        :error="form.errors.value.segment_id"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="customer-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
