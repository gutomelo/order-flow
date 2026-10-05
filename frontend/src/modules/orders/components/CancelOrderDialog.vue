<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextAreaField from '@/components/ui/TextAreaField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useCancelOrder } from '@/modules/orders/composables/useOrders'
import type { Order } from '@/modules/orders/types'
import { ApiError } from '@/services/http/apiError'

/** Cancelamento com motivo obrigatório (registrado no histórico do pedido). */
const open = defineModel<boolean>('open', { required: true })
const { order, title } = defineProps<{ order: Order; title: string }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const cancel = useCancelOrder()

const reason = ref('')
const reasonError = ref('')
const formError = ref<string | null>(null)

watch(open, (isOpen) => {
  if (!isOpen) return
  reason.value = ''
  reasonError.value = ''
  formError.value = null
})

async function onSubmit() {
  reasonError.value = reason.value.trim() ? '' : t('orders.cancel.reasonRequired')
  formError.value = null
  if (reasonError.value) {
    document.getElementById('cancel-reason')?.querySelector('textarea')?.focus()
    return
  }
  try {
    await cancel.mutateAsync({ id: order.id, reason: reason.value.trim() })
    toasts.success(t('orders.cancel.done'))
    open.value = false
  } catch (error) {
    if (error instanceof ApiError && error.details.field === 'reason')
      reasonError.value = error.message
    else formError.value = errorMessage(error)
  }
}
</script>

<template>
  <BaseDialog v-model:open="open" :title="title" :description="t('orders.cancel.description')">
    <form id="cancel-order-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="formError" />
      <div id="cancel-reason">
        <TextAreaField
          v-model="reason"
          :label="t('orders.cancel.reason')"
          :help="t('orders.cancel.reasonHelp')"
          :error="reasonError"
          :rows="3"
        />
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="cancel.isPending.value" @click="open = false">
        {{ t('orders.cancel.keep') }}
      </BaseButton>
      <BaseButton
        type="submit"
        form="cancel-order-form"
        variant="danger"
        :loading="cancel.isPending.value"
      >
        {{ t('orders.cancel.confirm') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
