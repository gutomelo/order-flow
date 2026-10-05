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
import { useSegmentOptions } from '@/modules/customers/composables/useCustomers'
import { useSavePriceList } from '@/modules/pricing/composables/usePricing'
import { priceListSchema } from '@/modules/pricing/schemas'
import type { PriceList } from '@/modules/pricing/types'

/** Criação (escolhe a quem a tabela se aplica) ou renomeação (o alvo não muda, regra PR7). */
const open = defineModel<boolean>('open', { required: true })
const { priceList = null, existing = [] } = defineProps<{
  priceList?: PriceList | null
  existing?: PriceList[]
}>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSavePriceList()
const segments = useSegmentOptions(() => priceList === null)

const isEdit = computed(() => priceList !== null)
const initialValues = { name: priceList?.name ?? '', target: isEdit.value ? 'fixed' : '' }
const form = useZodForm(priceListSchema, initialValues)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

// Só alvos ainda livres: uma tabela padrão e uma por segmento (PR1).
const targetOptions = computed(() => {
  const taken = new Set(existing.map((list) => list.segment?.id ?? 'default'))
  return [
    { value: '', label: t('pricing.form.chooseTarget') },
    ...(taken.has('default') ? [] : [{ value: 'default', label: t('pricing.form.defaultTarget') }]),
    ...(segments.data.value ?? [])
      .filter((segment) => segment.is_active && !taken.has(segment.id))
      .map((segment) => ({
        value: segment.id,
        label: t('pricing.form.segmentTarget', { name: segment.name }),
      })),
  ]
})

async function onSubmit() {
  const saved = await form.submit(
    (data) =>
      save.mutateAsync({
        id: priceList?.id,
        name: data.name,
        segment_id: data.target === 'default' ? null : data.target,
      }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(t(isEdit.value ? 'pricing.feedback.renamed' : 'pricing.feedback.created'))
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('pricing.form.renameTitle') : t('pricing.form.createTitle')"
    :description="isEdit ? undefined : t('pricing.form.createDescription')"
  >
    <form id="price-list-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />
      <TextField
        v-model="form.values.name"
        :label="t('pricing.fields.name')"
        required
        :error="form.errors.value.name"
      />
      <SelectField
        v-if="!isEdit"
        v-model="form.values.target"
        :label="t('pricing.fields.target')"
        :options="targetOptions"
        required
        :help="t('pricing.form.targetHelp')"
        :error="form.errors.value.target"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="price-list-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
