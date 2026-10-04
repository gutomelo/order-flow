<script setup lang="ts">
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSetReorderPoint } from '@/modules/inventory/composables/useInventory'
import { reorderPointSchema } from '@/modules/inventory/schemas/inventoryForms'
import type { StockItem } from '@/modules/inventory/types'

const open = defineModel<boolean>('open', { required: true })
const { item } = defineProps<{ item: StockItem }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSetReorderPoint()

const initial = { reorder_point: String(item.reorder_point) }
const form = useZodForm(reorderPointSchema, initial)
watch(open, (isOpen) => {
  if (isOpen) form.reset(initial)
})

async function onSubmit() {
  const saved = await form.submit(
    (data) => save.mutateAsync({ id: item.id, value: data.reorder_point }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(t('inventory.feedback.reorderPointSaved'))
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="t('inventory.reorderPoint.title')"
    :description="`${item.product.sku} — ${item.product.name} · ${item.warehouse.code}`"
  >
    <form id="reorder-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <p v-if="form.formError.value" class="text-sm font-medium text-danger" role="alert">
        {{ form.formError.value }}
      </p>
      <TextField
        v-model="form.values.reorder_point"
        :label="t('inventory.fields.reorderPoint')"
        inputmode="numeric"
        :help="t('inventory.reorderPoint.help')"
        :error="form.errors.value.reorder_point"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="reorder-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
