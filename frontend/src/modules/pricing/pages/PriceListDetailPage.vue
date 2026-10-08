<script setup lang="ts">
import { ArrowLeft, CircleSlash, PackageSearch, Pencil, Plus, Trash2 } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useSessionStore } from '@/modules/auth/stores/session'
import { PRICE_ITEMS_PAGE_SIZE } from '@/modules/pricing/api/pricingApi'
import PriceItemDialog from '@/modules/pricing/components/PriceItemDialog.vue'
import {
  usePriceItems,
  usePriceList,
  useRemovePriceItem,
} from '@/modules/pricing/composables/usePricing'
import type { PriceItemFilters, PriceListItem } from '@/modules/pricing/types'
import { ApiError } from '@/services/http/apiError'
import { formatMoney } from '@/utils/money'

const { id } = defineProps<{ id: string }>()

const { t } = useI18n()
const session = useSessionStore()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()
const canManage = computed(() => session.can('pricing:manage'))

const priceList = usePriceList(() => id)
const notFound = computed(
  () => priceList.error.value instanceof ApiError && priceList.error.value.status === 404,
)

const { filters, field, hasActiveFilters } = useUrlFilters<PriceItemFilters>({
  page: 1,
  search: '',
})
const search = field('search')
const page = field('page')
const items = usePriceItems(() => id, filters)

const columns = computed(() => [
  { key: 'product', label: t('pricing.items.product') },
  { key: 'unit_price', label: t('pricing.items.unitPrice'), align: 'right' as const },
  ...(canManage.value
    ? [{ key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const }]
    : []),
])

const dialogOpen = ref(false)
const editing = ref<PriceListItem | null>(null)
const dialogKey = computed(() => editing.value?.id ?? 'new')
function openDialog(item: PriceListItem | null) {
  editing.value = item
  dialogOpen.value = true
}

const remove = useRemovePriceItem(id)
const removing = ref<PriceListItem | null>(null)
const removeError = ref<string | null>(null)
const removeOpen = computed({
  get: () => removing.value !== null,
  set: (isOpen) => {
    if (!isOpen) removing.value = null
  },
})
function askRemove(item: PriceListItem) {
  removeError.value = null
  removing.value = item
}
async function confirmRemove() {
  const item = removing.value
  if (!item) return
  try {
    await remove.mutateAsync(item.id)
    toasts.success(t('pricing.items.feedback.removed', { sku: item.product.sku }))
    removing.value = null
  } catch (cause) {
    removeError.value = errorMessage(cause)
  }
}
</script>

<template>
  <div>
    <RouterLink
      :to="{ name: 'price-lists' }"
      class="mb-4 inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
    >
      <ArrowLeft class="size-4" aria-hidden="true" />
      {{ t('pricing.backToLists') }}
    </RouterLink>

    <EmptyState
      v-if="notFound"
      :title="t('pricing.notFoundTitle')"
      :description="t('pricing.notFoundDescription')"
    />
    <template v-else>
      <PageHeader
        :title="priceList.data.value?.name ?? t('common.loading')"
        :description="
          priceList.data.value?.is_default
            ? t('pricing.defaultListDescription')
            : t('pricing.segmentListDescription', {
                name: priceList.data.value?.segment?.name ?? '',
              })
        "
      >
        <template v-if="canManage" #actions>
          <BaseButton @click="openDialog(null)">
            <Plus class="size-4" aria-hidden="true" />
            {{ t('pricing.items.add') }}
          </BaseButton>
        </template>
      </PageHeader>

      <div class="mb-4 flex flex-wrap items-end gap-3">
        <SearchInput v-model="search" :label="t('pricing.items.search')" />
      </div>

      <DataTable
        v-model:page="page"
        :caption="t('pricing.items.caption')"
        :columns="columns"
        :rows="items.data.value?.results"
        :count="items.data.value?.count"
        :page-size="PRICE_ITEMS_PAGE_SIZE"
        :pending="items.isPending.value"
        :fetching="items.isFetching.value"
        :error="items.error.value ? errorMessage(items.error.value) : null"
        :error-title="t('pricing.items.errorTitle')"
        :empty-title="t('pricing.items.emptyTitle')"
        :empty-description="t('pricing.items.emptyDescription')"
        :empty-icon="PackageSearch"
        :filtered="hasActiveFilters"
        min-width="520px"
        @retry="items.refetch()"
      >
        <template v-if="canManage" #empty-action>
          <BaseButton @click="openDialog(null)">{{ t('pricing.items.add') }}</BaseButton>
        </template>
        <template #cell-product="{ row }">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-mono text-xs text-text-secondary">{{ row.product.sku }}</span>
            <span>{{ row.product.name }}</span>
            <StatusBadge
              v-if="!row.product.is_active"
              :label="t('common.status.inactive')"
              :icon="CircleSlash"
              tone="neutral"
            />
          </div>
        </template>
        <template #cell-unit_price="{ row }">
          <span class="tabular-nums">{{ formatMoney(row.unit_price) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex justify-end gap-1">
            <BaseButton variant="ghost" size="sm" @click="openDialog(row)">
              <Pencil class="size-4" aria-hidden="true" />
              <span class="sr-only">{{
                t('pricing.items.editItem', { sku: row.product.sku })
              }}</span>
            </BaseButton>
            <BaseButton variant="ghost" size="sm" @click="askRemove(row)">
              <Trash2 class="size-4" aria-hidden="true" />
              <span class="sr-only">{{ t('common.removeItem', { name: row.product.sku }) }}</span>
            </BaseButton>
          </div>
        </template>
      </DataTable>

      <PriceItemDialog
        v-if="canManage"
        :key="dialogKey"
        v-model:open="dialogOpen"
        :price-list-id="id"
        :item="editing"
      />
      <ConfirmDialog
        v-model:open="removeOpen"
        :title="t('pricing.items.confirmRemoveTitle', { sku: removing?.product.sku })"
        :description="t('pricing.items.confirmRemove')"
        :confirm-label="t('common.remove')"
        :loading="remove.isPending.value"
        :error="removeError"
        @confirm="confirmRemove"
      />
    </template>
  </div>
</template>
