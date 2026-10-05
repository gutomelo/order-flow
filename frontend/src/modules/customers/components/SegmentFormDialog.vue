<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextAreaField from '@/components/ui/TextAreaField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSaveSegment } from '@/modules/customers/composables/useCustomers'
import { segmentSchema } from '@/modules/customers/schemas/customerForms'
import type { Segment } from '@/modules/customers/types'

const open = defineModel<boolean>('open', { required: true })
const { segment = null } = defineProps<{ segment?: Segment | null }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSaveSegment()

const isEdit = computed(() => segment !== null)
const initialValues = {
  code: segment?.code ?? '',
  name: segment?.name ?? '',
  description: segment?.description ?? '',
}
const form = useZodForm(segmentSchema, initialValues)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

async function onSubmit() {
  const saved = await form.submit(
    (data) => save.mutateAsync({ id: segment?.id, data }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(t(isEdit.value ? 'segments.feedback.updated' : 'segments.feedback.created'))
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('segments.form.editTitle') : t('segments.form.createTitle')"
  >
    <form id="segment-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />
      <!-- O código é imutável (identifica o segmento em tabelas de preço): só na criação. -->
      <TextField
        v-if="!isEdit"
        v-model="form.values.code"
        :label="t('segments.fields.code')"
        required
        :help="t('segments.form.codeHelp')"
        :error="form.errors.value.code"
      />
      <p v-else class="text-sm">
        <span class="text-text-secondary">{{ t('segments.fields.code') }}:</span>
        <span class="ml-1 font-mono">{{ segment?.code }}</span>
      </p>
      <TextField
        v-model="form.values.name"
        :label="t('segments.fields.name')"
        required
        :error="form.errors.value.name"
      />
      <TextAreaField
        v-model="form.values.description"
        :label="t('segments.fields.description')"
        :error="form.errors.value.description"
        :rows="2"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="segment-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
