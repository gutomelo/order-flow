<script setup lang="ts">
import { CircleCheck, CircleSlash, FolderTree, Pencil, Plus } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useActivationToggle } from '@/composables/useActivationToggle'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useSessionStore } from '@/modules/auth/stores/session'
import CategoryFormDialog from '@/modules/catalog/components/CategoryFormDialog.vue'
import { useCategories, useSetCategoryActive } from '@/modules/catalog/composables/useCatalog'
import { MAX_CATEGORY_DEPTH, type Category } from '@/modules/catalog/types'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canManage = computed(() => session.can('catalog:manage'))

const { data, isPending, error, refetch, isFetching } = useCategories()

const columns = computed(() => [
  { key: 'name', label: t('catalog.fields.name') },
  { key: 'status', label: t('common.status.label') },
  ...(canManage.value
    ? [{ key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const }]
    : []),
])

const formOpen = ref(false)
const editing = ref<Category | null>(null)
const newParentId = ref<string | null>(null)
const formKey = computed(() => `${editing.value?.id ?? 'new'}:${newParentId.value ?? ''}`)

function openCreate(parent: Category | null) {
  editing.value = null
  newParentId.value = parent?.id ?? null
  formOpen.value = true
}
function openEdit(category: Category) {
  editing.value = category
  newParentId.value = null
  formOpen.value = true
}

const setActive = useSetCategoryActive()
const toggle = useActivationToggle<Category>({
  mutate: (input) => setActive.mutateAsync(input),
  successMessage: (category) =>
    t(
      category.is_active
        ? 'catalog.feedback.categoryDeactivated'
        : 'catalog.feedback.categoryActivated',
    ),
})
</script>

<template>
  <div>
    <PageHeader
      :title="t('catalog.categories.title')"
      :description="t('catalog.categories.description')"
    >
      <template v-if="canManage" #actions>
        <BaseButton @click="openCreate(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('catalog.actions.createCategory') }}
        </BaseButton>
      </template>
    </PageHeader>

    <DataTable
      :caption="t('catalog.categories.title')"
      :columns="columns"
      :rows="data"
      :paginated="false"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('catalog.categories.errorTitle')"
      :empty-title="t('catalog.categories.emptyTitle')"
      :empty-description="t('catalog.categories.emptyDescription')"
      :empty-icon="FolderTree"
      min-width="560px"
      @retry="refetch()"
    >
      <template v-if="canManage" #empty-action>
        <BaseButton @click="openCreate(null)">{{ t('catalog.actions.createCategory') }}</BaseButton>
      </template>
      <template #cell-name="{ row }">
        <!-- Indentação visual + caminho completo para leitores de tela. -->
        <span class="font-medium" :style="{ paddingLeft: `${(row.depth - 1) * 1.5}rem` }">
          <span aria-hidden="true">
            <span v-if="row.depth > 1" class="text-text-secondary">└ </span>{{ row.name }}
          </span>
          <span class="sr-only">{{ row.path }}</span>
        </span>
      </template>
      <template #cell-status="{ row }">
        <StatusBadge
          :label="row.is_active ? t('common.status.active') : t('common.status.inactive')"
          :icon="row.is_active ? CircleCheck : CircleSlash"
          :tone="row.is_active ? 'success' : 'neutral'"
        />
      </template>
      <template #cell-actions="{ row }">
        <div class="flex justify-end gap-1">
          <BaseButton
            v-if="row.is_active && row.depth < MAX_CATEGORY_DEPTH"
            variant="ghost"
            size="sm"
            @click="openCreate(row)"
          >
            <Plus class="size-4" aria-hidden="true" />
            <span class="sr-only">{{
              t('catalog.actions.addSubcategory', { name: row.path })
            }}</span>
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="openEdit(row)">
            <Pencil class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('common.editItem', { name: row.path }) }}</span>
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="toggle.ask(row)">
            <component
              :is="row.is_active ? CircleSlash : CircleCheck"
              class="size-4"
              aria-hidden="true"
            />
            <span class="sr-only">
              {{
                row.is_active
                  ? t('common.deactivateItem', { name: row.path })
                  : t('common.activateItem', { name: row.path })
              }}
            </span>
          </BaseButton>
        </div>
      </template>
    </DataTable>

    <CategoryFormDialog
      v-if="canManage && data"
      :key="formKey"
      v-model:open="formOpen"
      :category="editing"
      :parent-id="newParentId"
      :categories="data"
    />

    <ConfirmDialog
      v-model:open="toggle.open.value"
      :title="
        toggle.target.value?.is_active
          ? t('common.confirmDeactivateTitle', { name: toggle.target.value?.path })
          : t('common.confirmActivateTitle', { name: toggle.target.value?.path })
      "
      :description="
        toggle.target.value?.is_active
          ? t('catalog.confirm.deactivateCategory')
          : t('catalog.confirm.activateCategory')
      "
      :confirm-label="
        toggle.target.value?.is_active ? t('common.deactivate') : t('common.activate')
      "
      :tone="toggle.target.value?.is_active ? 'danger' : 'primary'"
      :loading="toggle.running.value"
      @confirm="toggle.confirm"
    />
  </div>
</template>
