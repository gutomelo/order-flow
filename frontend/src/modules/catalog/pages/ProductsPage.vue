<script setup lang="ts">
import { CircleCheck, CircleSlash, Package, Pencil, Plus } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectField from '@/components/ui/SelectField.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useActivationToggle } from '@/composables/useActivationToggle'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useSessionStore } from '@/modules/auth/stores/session'
import { PRODUCTS_PAGE_SIZE } from '@/modules/catalog/api/catalogApi'
import ProductFormDialog from '@/modules/catalog/components/ProductFormDialog.vue'
import {
  useCategories,
  useProductsList,
  useSetProductActive,
} from '@/modules/catalog/composables/useCatalog'
import type { Product, ProductFilters, StatusFilter } from '@/modules/catalog/types'
import { useSupplierOptions } from '@/modules/suppliers/composables/useSuppliers'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canManage = computed(() => session.can('catalog:manage'))
// SALES lê o catálogo, mas não fornecedores: sem a permissão, nem consulta a lista.
const canSeeSuppliers = session.can('suppliers:read')

const { filters, field, hasActiveFilters } = useUrlFilters<ProductFilters>(
  { page: 1, search: '', category: '', supplier: '', status: '' },
  { status: (raw) => (raw === 'active' || raw === 'inactive' ? (raw as StatusFilter) : undefined) },
)
const search = field('search')
const category = field('category')
const supplier = field('supplier')
const status = field('status')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useProductsList(filters)
const categories = useCategories()
const suppliers = canSeeSuppliers ? useSupplierOptions() : null

const categoryOptions = computed(() => [
  { value: '', label: t('catalog.filters.allCategories') },
  ...(categories.data.value ?? []).map((c) => ({ value: c.id, label: c.path })),
])
const supplierOptions = computed(() => [
  { value: '', label: t('catalog.filters.allSuppliers') },
  ...(suppliers?.data.value ?? []).map((s) => ({ value: s.id, label: s.display_name })),
])
const statusOptions = computed(() => [
  { value: '', label: t('common.allStatuses') },
  { value: 'active', label: t('common.status.active') },
  { value: 'inactive', label: t('common.status.inactive') },
])
const columns = computed(() => [
  { key: 'product', label: t('catalog.fields.product') },
  { key: 'category', label: t('catalog.fields.category') },
  { key: 'unit', label: t('catalog.fields.unit') },
  ...(canSeeSuppliers ? [{ key: 'supplier', label: t('catalog.fields.defaultSupplier') }] : []),
  { key: 'status', label: t('common.status.label') },
  ...(canManage.value
    ? [{ key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const }]
    : []),
])

const formOpen = ref(false)
const editing = ref<Product | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')
function openForm(product: Product | null) {
  editing.value = product
  formOpen.value = true
}

const setActive = useSetProductActive()
const toggle = useActivationToggle<Product>({
  mutate: (input) => setActive.mutateAsync(input),
  successMessage: (product) =>
    t(
      product.is_active
        ? 'catalog.feedback.productDeactivated'
        : 'catalog.feedback.productActivated',
    ),
})
</script>

<template>
  <div>
    <PageHeader
      :title="t('catalog.products.title')"
      :description="t('catalog.products.description')"
    >
      <template v-if="canManage" #actions>
        <BaseButton @click="openForm(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('catalog.actions.createProduct') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('catalog.filters.search')" />
      <SelectField
        v-model="category"
        :label="t('catalog.fields.category')"
        :options="categoryOptions"
        hide-label
      />
      <SelectField
        v-if="canSeeSuppliers"
        v-model="supplier"
        :label="t('catalog.fields.defaultSupplier')"
        :options="supplierOptions"
        hide-label
      />
      <SelectField
        v-model="status"
        :label="t('common.status.label')"
        :options="statusOptions"
        hide-label
      />
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('catalog.products.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="PRODUCTS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('catalog.products.errorTitle')"
      :empty-title="t('catalog.products.emptyTitle')"
      :empty-description="
        canManage ? t('catalog.products.emptyDescription') : t('catalog.products.emptyReadOnly')
      "
      :empty-icon="Package"
      :filtered="hasActiveFilters"
      @retry="refetch()"
    >
      <template v-if="canManage" #empty-action>
        <BaseButton @click="openForm(null)">{{ t('catalog.actions.createProduct') }}</BaseButton>
      </template>
      <template #cell-product="{ row }">
        <p class="font-medium">{{ row.name }}</p>
        <p class="font-mono text-xs text-text-secondary">{{ row.sku }}</p>
      </template>
      <template #cell-category="{ row }">
        <span v-if="row.category" :class="{ 'text-text-secondary': !row.category.is_active }">
          {{ row.category.path }}
        </span>
        <span v-else class="text-text-secondary">—</span>
      </template>
      <template #cell-unit="{ row }">{{ t(`catalog.units.${row.unit}`) }}</template>
      <template #cell-supplier="{ row }">
        <!-- Texto único: nós separados perderiam o espaço ("Sul Expressinativo"). -->
        <span
          v-if="row.default_supplier"
          :class="{ 'text-text-secondary': !row.default_supplier.is_active }"
        >
          {{
            row.default_supplier.is_active
              ? row.default_supplier.display_name
              : `${row.default_supplier.display_name} (${t('common.status.inactive').toLowerCase()})`
          }}
        </span>
        <span v-else class="text-text-secondary">—</span>
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
          <BaseButton variant="ghost" size="sm" @click="openForm(row)">
            <Pencil class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('common.editItem', { name: row.name }) }}</span>
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
                  ? t('common.deactivateItem', { name: row.name })
                  : t('common.activateItem', { name: row.name })
              }}
            </span>
          </BaseButton>
        </div>
      </template>
    </DataTable>

    <ProductFormDialog v-if="canManage" :key="formKey" v-model:open="formOpen" :product="editing" />

    <ConfirmDialog
      v-model:open="toggle.open.value"
      :title="
        toggle.target.value?.is_active
          ? t('common.confirmDeactivateTitle', { name: toggle.target.value?.name })
          : t('common.confirmActivateTitle', { name: toggle.target.value?.name })
      "
      :description="
        toggle.target.value?.is_active
          ? t('catalog.confirm.deactivateProduct')
          : t('catalog.confirm.activateProduct')
      "
      :confirm-label="
        toggle.target.value?.is_active ? t('common.deactivate') : t('common.activate')
      "
      :tone="toggle.target.value?.is_active ? 'danger' : 'primary'"
      :loading="toggle.running.value"
      :error="toggle.error.value"
      @confirm="toggle.confirm"
    />
  </div>
</template>
