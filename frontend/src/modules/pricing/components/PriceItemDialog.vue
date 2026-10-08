<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import FormAlert from '@/components/ui/FormAlert.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import ProductPicker, { type ProductOption } from '@/modules/catalog/components/ProductPicker.vue'
import { useSavePriceItem } from '@/modules/pricing/composables/usePricing'
import { priceItemSchema } from '@/modules/pricing/schemas'
import type { PriceListItem } from '@/modules/pricing/types'
import { ApiError } from '@/services/http/apiError'
import { toMoneyInput } from '@/utils/money'

/** Sem `item`: inclui um produto na tabela; com `item`: altera o preço. */
const open = defineModel<boolean>('open', { required: true })
const { priceListId, item = null } = defineProps<{
  priceListId: string
  item?: PriceListItem | null
}>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSavePriceItem(priceListId)

const isEdit = computed(() => item !== null)
const product = ref<ProductOption | null>(null)
const productError = ref('')
const initialValues = { unit_price: item ? toMoneyInput(item.unit_price) : '' }
const form = useZodForm(priceItemSchema, initialValues)

watch(open, (isOpen) => {
  if (!isOpen) return
  form.reset(initialValues)
  product.value = null
  productError.value = ''
})

async function onSubmit() {
  productError.value = !isEdit.value && !product.value ? t('validation.required') : ''
  if (productError.value) return
  const saved = await form.submit(
    (data) =>
      save.mutateAsync({
        id: item?.id,
        product_id: product.value?.id,
        unit_price: data.unit_price,
      }),
    (error) => {
      // Erros do produto (inativo, já na tabela) aparecem no próprio seletor.
      if (error instanceof ApiError && error.details.field === 'product_id') {
        productError.value = error.message
        return
      }
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(
      t(isEdit.value ? 'pricing.items.feedback.updated' : 'pricing.items.feedback.added'),
    )
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('pricing.items.editTitle') : t('pricing.items.addTitle')"
    :description="item ? `${item.product.sku} — ${item.product.name}` : undefined"
  >
    <form id="price-item-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <FormAlert :message="form.formError.value" />
      <ProductPicker
        v-if="!isEdit"
        v-model="product"
        :label="t('pricing.items.product')"
        :error="productError"
      />
      <TextField
        v-model="form.values.unit_price"
        :label="t('pricing.items.unitPrice')"
        inputmode="decimal"
        required
        :help="t('pricing.items.unitPriceHelp')"
        :error="form.errors.value.unit_price"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="price-item-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
