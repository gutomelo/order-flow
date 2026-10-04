<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSaveSupplier } from '@/modules/suppliers/composables/useSuppliers'
import { supplierSchema } from '@/modules/suppliers/schemas/supplierForm'
import type { Supplier } from '@/modules/suppliers/types'

/** Sem `supplier`: criação; com `supplier`: edição. Recriado pelo pai via `key`. */
const open = defineModel<boolean>('open', { required: true })
const { supplier = null } = defineProps<{ supplier?: Supplier | null }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSaveSupplier()

const initialValues = {
  legal_name: supplier?.legal_name ?? '',
  trade_name: supplier?.trade_name ?? '',
  tax_id: supplier?.tax_id_formatted ?? '',
  email: supplier?.email ?? '',
  phone: supplier?.phone ?? '',
}
const form = useZodForm(supplierSchema, initialValues)
const isEdit = computed(() => supplier !== null)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

async function onSubmit() {
  const saved = await form.submit(
    (data) => save.mutateAsync({ id: supplier?.id, data }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(t(isEdit.value ? 'suppliers.feedback.updated' : 'suppliers.feedback.created'))
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('suppliers.form.editTitle') : t('suppliers.form.createTitle')"
  >
    <form id="supplier-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <div
        v-if="form.formError.value"
        class="flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm"
        role="alert"
      >
        <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
        {{ form.formError.value }}
      </div>
      <TextField
        v-model="form.values.legal_name"
        :label="t('suppliers.fields.legalName')"
        required
        :error="form.errors.value.legal_name"
      />
      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.trade_name"
          :label="t('suppliers.fields.tradeName')"
          :error="form.errors.value.trade_name"
        />
        <TextField
          v-model="form.values.tax_id"
          :label="t('suppliers.fields.taxId')"
          required
          :help="t('suppliers.form.taxIdHelp')"
          :error="form.errors.value.tax_id"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <TextField
          v-model="form.values.email"
          type="email"
          :label="t('suppliers.fields.email')"
          :error="form.errors.value.email"
        />
        <TextField
          v-model="form.values.phone"
          :label="t('suppliers.fields.phone')"
          autocomplete="off"
          :error="form.errors.value.phone"
        />
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="supplier-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
