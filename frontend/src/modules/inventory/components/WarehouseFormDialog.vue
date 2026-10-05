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
import { useSaveWarehouse } from '@/modules/inventory/composables/useInventory'
import { warehouseSchema } from '@/modules/inventory/schemas/inventoryForms'
import type { Warehouse } from '@/modules/inventory/types'

/** Criação ou renomeação (o código não muda depois de criado). Recriado via `key`. */
const open = defineModel<boolean>('open', { required: true })
const { warehouse = null } = defineProps<{ warehouse?: Warehouse | null }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSaveWarehouse()

const initial = { code: warehouse?.code ?? '', name: warehouse?.name ?? '' }
const form = useZodForm(warehouseSchema, initial)
const isEdit = computed(() => warehouse !== null)
watch(open, (isOpen) => {
  if (isOpen) form.reset(initial)
})

async function onSubmit() {
  const saved = await form.submit(
    (data) => save.mutateAsync({ id: warehouse?.id, ...data }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(
      t(
        isEdit.value
          ? 'inventory.feedback.warehouseUpdated'
          : 'inventory.feedback.warehouseCreated',
      ),
    )
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('inventory.warehouses.editTitle') : t('inventory.warehouses.createTitle')"
  >
    <form id="warehouse-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />
      <TextField
        v-if="!isEdit"
        v-model="form.values.code"
        :label="t('inventory.fields.code')"
        required
        :help="t('inventory.warehouses.codeHelp')"
        :error="form.errors.value.code"
      />
      <TextField
        v-model="form.values.name"
        :label="t('inventory.fields.name')"
        required
        :error="form.errors.value.name"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="warehouse-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
