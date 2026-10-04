<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextAreaField from '@/components/ui/TextAreaField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { useSessionStore } from '@/modules/auth/stores/session'
import { useCategories, useSaveProduct } from '@/modules/catalog/composables/useCatalog'
import { productSchema } from '@/modules/catalog/schemas/catalogForms'
import { UNITS, type Product } from '@/modules/catalog/types'
import { useSupplierOptions } from '@/modules/suppliers/composables/useSuppliers'

/** Sem `product`: criação; com `product`: edição (SKU somente leitura). Recriado via `key`. */
const open = defineModel<boolean>('open', { required: true })
const { product = null } = defineProps<{ product?: Product | null }>()

const { t } = useI18n()
const toasts = useToastStore()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const save = useSaveProduct()
const categories = useCategories()
const canSeeSuppliers = session.can('suppliers:read')
const suppliers = canSeeSuppliers ? useSupplierOptions() : null

const initialValues = {
  sku: product?.sku ?? '',
  name: product?.name ?? '',
  description: product?.description ?? '',
  unit: product?.unit ?? 'UNIT',
  barcode: product?.barcode ?? '',
  category_id: product?.category?.id ?? '',
  default_supplier_id: product?.default_supplier?.id ?? '',
}
const form = useZodForm(productSchema, initialValues)
const isEdit = computed(() => product !== null)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

const unitOptions = computed(() =>
  UNITS.map((unit) => ({ value: unit, label: t(`catalog.units.${unit}`) })),
)
// Só categorias/fornecedores ativos podem ser atribuídos (regra C4).
const categoryOptions = computed(() => [
  { value: '', label: t('catalog.form.noCategory') },
  ...(categories.data.value ?? [])
    .filter((category) => category.is_active)
    .map((category) => ({ value: category.id, label: category.path })),
])
const supplierOptions = computed(() => [
  { value: '', label: t('catalog.form.noSupplier') },
  ...(suppliers?.data.value ?? []).map((supplier) => ({
    value: supplier.id,
    label: supplier.display_name,
  })),
])

async function onSubmit() {
  const saved = await form.submit(
    (data) =>
      save.mutateAsync({
        id: product?.id,
        data: {
          ...data,
          category_id: data.category_id || null,
          default_supplier_id: data.default_supplier_id || null,
        },
      }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(
      t(isEdit.value ? 'catalog.feedback.productUpdated' : 'catalog.feedback.productCreated'),
    )
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('catalog.form.editProduct') : t('catalog.form.createProduct')"
    :description="isEdit ? `SKU ${product?.sku}` : t('catalog.form.createProductDescription')"
  >
    <form id="product-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <div
        v-if="form.formError.value"
        class="flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm"
        role="alert"
      >
        <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
        {{ form.formError.value }}
      </div>
      <div class="grid gap-4 sm:grid-cols-3">
        <TextField
          v-if="!isEdit"
          v-model="form.values.sku"
          :label="t('catalog.fields.sku')"
          required
          :help="t('catalog.form.skuHelp')"
          :error="form.errors.value.sku"
        />
        <TextField
          v-model="form.values.name"
          class="sm:col-span-2"
          :class="{ 'sm:col-span-3': isEdit }"
          :label="t('catalog.fields.name')"
          required
          :error="form.errors.value.name"
        />
      </div>
      <TextAreaField
        v-model="form.values.description"
        :label="t('catalog.fields.description')"
        :error="form.errors.value.description"
      />
      <div class="grid gap-4 sm:grid-cols-2">
        <SelectField
          v-model="form.values.unit"
          :label="t('catalog.fields.unit')"
          :options="unitOptions"
          required
        />
        <TextField
          v-model="form.values.barcode"
          :label="t('catalog.fields.barcode')"
          :help="t('catalog.form.barcodeHelp')"
          :error="form.errors.value.barcode"
        />
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <SelectField
          v-model="form.values.category_id"
          :label="t('catalog.fields.category')"
          :options="categoryOptions"
          :error="form.errors.value.category_id"
        />
        <SelectField
          v-if="canSeeSuppliers"
          v-model="form.values.default_supplier_id"
          :label="t('catalog.fields.defaultSupplier')"
          :options="supplierOptions"
          :error="form.errors.value.default_supplier_id"
        />
      </div>
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="product-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
