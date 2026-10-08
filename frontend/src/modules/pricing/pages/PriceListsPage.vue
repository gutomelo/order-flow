<script setup lang="ts">
import { BadgeDollarSign, Pencil, Plus, Star, Tags, Trash2 } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useSessionStore } from '@/modules/auth/stores/session'
import PriceListFormDialog from '@/modules/pricing/components/PriceListFormDialog.vue'
import { useDeletePriceList, usePriceLists } from '@/modules/pricing/composables/usePricing'
import type { PriceList } from '@/modules/pricing/types'

const { t } = useI18n()
const session = useSessionStore()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const canManage = computed(() => session.can('pricing:manage'))

const { data, isPending, error, refetch, isFetching } = usePriceLists()

const columns = computed(() => [
  { key: 'name', label: t('pricing.fields.name') },
  { key: 'target', label: t('pricing.fields.target') },
  { key: 'items_count', label: t('pricing.fields.itemsCount'), align: 'right' as const },
  ...(canManage.value
    ? [{ key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const }]
    : []),
])

const formOpen = ref(false)
const editing = ref<PriceList | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')
function openForm(priceList: PriceList | null) {
  editing.value = priceList
  formOpen.value = true
}

const remove = useDeletePriceList()
const removing = ref<PriceList | null>(null)
const removeError = ref<string | null>(null)
const removeOpen = computed({
  get: () => removing.value !== null,
  set: (isOpen) => {
    if (!isOpen) removing.value = null
  },
})
function askRemove(priceList: PriceList) {
  removeError.value = null
  removing.value = priceList
}
async function confirmRemove() {
  const priceList = removing.value
  if (!priceList) return
  try {
    await remove.mutateAsync(priceList.id)
    toasts.success(t('pricing.feedback.deleted', { name: priceList.name }))
    removing.value = null
  } catch (cause) {
    removeError.value = errorMessage(cause)
  }
}
</script>

<template>
  <div>
    <PageHeader :title="t('pricing.title')" :description="t('pricing.description')">
      <template v-if="canManage" #actions>
        <BaseButton @click="openForm(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('pricing.actions.create') }}
        </BaseButton>
      </template>
    </PageHeader>

    <DataTable
      :caption="t('pricing.title')"
      :columns="columns"
      :rows="data"
      :paginated="false"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('pricing.error.title')"
      :empty-title="t('pricing.empty.title')"
      :empty-description="t('pricing.empty.description')"
      :empty-icon="BadgeDollarSign"
      min-width="560px"
      @retry="refetch()"
    >
      <template v-if="canManage" #empty-action>
        <BaseButton @click="openForm(null)">{{ t('pricing.actions.create') }}</BaseButton>
      </template>
      <template #cell-name="{ row }">
        <RouterLink
          :to="{ name: 'price-list-detail', params: { id: row.id } }"
          class="font-medium text-link underline-offset-2 hover:underline"
        >
          {{ row.name }}
        </RouterLink>
      </template>
      <template #cell-target="{ row }">
        <StatusBadge
          v-if="row.is_default"
          :label="t('pricing.defaultList')"
          :icon="Star"
          tone="info"
        />
        <StatusBadge
          v-else
          :label="
            row.segment?.is_active
              ? row.segment.name
              : t('customers.inactiveName', { name: row.segment?.name })
          "
          :icon="Tags"
          tone="neutral"
        />
      </template>
      <template #cell-items_count="{ row }">
        <span class="tabular-nums">{{ row.items_count }}</span>
      </template>
      <template #cell-actions="{ row }">
        <div class="flex justify-end gap-1">
          <BaseButton variant="ghost" size="sm" @click="openForm(row)">
            <Pencil class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('pricing.actions.rename', { name: row.name }) }}</span>
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="askRemove(row)">
            <Trash2 class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('common.removeItem', { name: row.name }) }}</span>
          </BaseButton>
        </div>
      </template>
    </DataTable>

    <PriceListFormDialog
      v-if="canManage"
      :key="formKey"
      v-model:open="formOpen"
      :price-list="editing"
      :existing="data ?? []"
    />
    <ConfirmDialog
      v-model:open="removeOpen"
      :title="t('pricing.confirmDeleteTitle', { name: removing?.name })"
      :description="
        removing?.is_default
          ? t('pricing.confirmDeleteDefault', { count: removing?.items_count ?? 0 })
          : t('pricing.confirmDelete', { count: removing?.items_count ?? 0 })
      "
      :confirm-label="t('common.remove')"
      :loading="remove.isPending.value"
      :error="removeError"
      @confirm="confirmRemove"
    />
  </div>
</template>
