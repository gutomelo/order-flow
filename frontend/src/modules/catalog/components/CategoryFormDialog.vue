<script setup lang="ts">
import { CircleAlert } from '@lucide/vue'
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseDialog from '@/components/ui/BaseDialog.vue'
import SelectField from '@/components/ui/SelectField.vue'
import TextField from '@/components/ui/TextField.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useZodForm } from '@/composables/useZodForm'
import { subtreeIds, useSaveCategory } from '@/modules/catalog/composables/useCatalog'
import { categorySchema } from '@/modules/catalog/schemas/catalogForms'
import { MAX_CATEGORY_DEPTH, type Category } from '@/modules/catalog/types'

/**
 * Cria (opcionalmente sob `parentId`) ou renomeia/move `category`. Recriado via `key`.
 * As opções de "categoria superior" antecipam as regras do backend (profundidade e ciclos).
 */
const open = defineModel<boolean>('open', { required: true })
const {
  category = null,
  parentId = null,
  categories,
} = defineProps<{ category?: Category | null; parentId?: string | null; categories: Category[] }>()

const { t } = useI18n()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const save = useSaveCategory()

const initialValues = {
  name: category?.name ?? '',
  parent_id: category ? (category.parent_id ?? '') : (parentId ?? ''),
}
const form = useZodForm(categorySchema, initialValues)
const isEdit = computed(() => category !== null)

watch(open, (isOpen) => {
  if (isOpen) form.reset(initialValues)
})

// Altura da subárvore movida: a nova posição + altura não pode passar de 3 níveis.
const subtree = computed(() => (category ? subtreeIds(categories, category.id) : new Set<string>()))
const subtreeHeight = computed(() => {
  if (!category) return 0
  const depths = categories.filter((c) => subtree.value.has(c.id)).map((c) => c.depth)
  return Math.max(category.depth, ...depths) - category.depth
})
const parentOptions = computed(() => [
  { value: '', label: t('catalog.categories.rootLevel') },
  ...categories
    .filter(
      (candidate) =>
        candidate.is_active &&
        !subtree.value.has(candidate.id) &&
        candidate.depth + 1 + subtreeHeight.value <= MAX_CATEGORY_DEPTH,
    )
    .map((candidate) => ({ value: candidate.id, label: candidate.path })),
])

async function onSubmit() {
  const saved = await form.submit(
    (data) =>
      save.mutateAsync({ id: category?.id, name: data.name, parentId: data.parent_id || null }),
    (error) => {
      form.formError.value = errorMessage(error)
    },
  )
  if (saved) {
    toasts.success(
      t(isEdit.value ? 'catalog.feedback.categoryUpdated' : 'catalog.feedback.categoryCreated'),
    )
    open.value = false
  }
}
</script>

<template>
  <BaseDialog
    v-model:open="open"
    :title="isEdit ? t('catalog.categories.editTitle') : t('catalog.categories.createTitle')"
  >
    <form id="category-form" class="flex flex-col gap-4" novalidate @submit.prevent="onSubmit">
      <div
        v-if="form.formError.value"
        class="flex items-start gap-2 rounded-md border border-danger/40 p-3 text-sm"
        role="alert"
      >
        <CircleAlert class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
        {{ form.formError.value }}
      </div>
      <TextField
        v-model="form.values.name"
        :label="t('catalog.fields.name')"
        required
        :error="form.errors.value.name"
      />
      <SelectField
        v-model="form.values.parent_id"
        :label="t('catalog.categories.parent')"
        :options="parentOptions"
        :help="t('catalog.categories.parentHelp')"
        :error="form.errors.value.parent_id"
      />
    </form>
    <template #footer>
      <BaseButton variant="secondary" :disabled="form.isSubmitting.value" @click="open = false">
        {{ t('common.cancel') }}
      </BaseButton>
      <BaseButton type="submit" form="category-form" :loading="form.isSubmitting.value">
        {{ t('common.save') }}
      </BaseButton>
    </template>
  </BaseDialog>
</template>
