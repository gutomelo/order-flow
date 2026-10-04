<script setup lang="ts">
import { CircleCheck, CircleSlash, Pencil, Plus, Truck } from '@lucide/vue'
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
import { SUPPLIERS_PAGE_SIZE } from '@/modules/suppliers/api/suppliersApi'
import SupplierFormDialog from '@/modules/suppliers/components/SupplierFormDialog.vue'
import {
  useSetSupplierActive,
  useSuppliersList,
} from '@/modules/suppliers/composables/useSuppliers'
import type { StatusFilter, Supplier, SupplierFilters } from '@/modules/suppliers/types'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canManage = computed(() => session.can('suppliers:manage'))

const { filters, field, hasActiveFilters } = useUrlFilters<SupplierFilters>(
  { page: 1, search: '', status: '' },
  { status: (raw) => (raw === 'active' || raw === 'inactive' ? (raw as StatusFilter) : undefined) },
)
const search = field('search')
const status = field('status')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useSuppliersList(filters)

const statusOptions = computed(() => [
  { value: '', label: t('common.allStatuses') },
  { value: 'active', label: t('common.status.active') },
  { value: 'inactive', label: t('common.status.inactive') },
])
const columns = computed(() => [
  { key: 'name', label: t('suppliers.fields.name') },
  { key: 'tax_id_formatted', label: t('suppliers.fields.taxId') },
  { key: 'contact', label: t('suppliers.fields.contact') },
  { key: 'status', label: t('common.status.label') },
  ...(canManage.value
    ? [{ key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const }]
    : []),
])

const formOpen = ref(false)
const editing = ref<Supplier | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')
function openForm(supplier: Supplier | null) {
  editing.value = supplier
  formOpen.value = true
}

const setActive = useSetSupplierActive()
const toggle = useActivationToggle<Supplier>({
  mutate: (input) => setActive.mutateAsync(input),
  successMessage: (supplier) =>
    t(supplier.is_active ? 'suppliers.feedback.deactivated' : 'suppliers.feedback.activated'),
})
</script>

<template>
  <div>
    <PageHeader :title="t('suppliers.title')" :description="t('suppliers.description')">
      <template v-if="canManage" #actions>
        <BaseButton @click="openForm(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('suppliers.actions.create') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('suppliers.filters.search')" />
      <SelectField
        v-model="status"
        :label="t('common.status.label')"
        :options="statusOptions"
        hide-label
      />
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('suppliers.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="SUPPLIERS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('suppliers.error.title')"
      :empty-title="t('suppliers.empty.title')"
      :empty-description="t('suppliers.empty.description')"
      :empty-icon="Truck"
      :filtered="hasActiveFilters"
      @retry="refetch()"
    >
      <template v-if="canManage" #empty-action>
        <BaseButton @click="openForm(null)">{{ t('suppliers.actions.create') }}</BaseButton>
      </template>
      <template #cell-name="{ row }">
        <p class="font-medium">{{ row.display_name }}</p>
        <p v-if="row.trade_name" class="text-xs text-text-secondary">{{ row.legal_name }}</p>
      </template>
      <template #cell-tax_id_formatted="{ row }">
        <span class="tabular-nums">{{ row.tax_id_formatted }}</span>
      </template>
      <template #cell-contact="{ row }">
        <p>{{ row.email || '—' }}</p>
        <p v-if="row.phone" class="text-xs text-text-secondary">{{ row.phone }}</p>
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
            <span class="sr-only">{{ t('common.editItem', { name: row.display_name }) }}</span>
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
                  ? t('common.deactivateItem', { name: row.display_name })
                  : t('common.activateItem', { name: row.display_name })
              }}
            </span>
          </BaseButton>
        </div>
      </template>
    </DataTable>

    <SupplierFormDialog
      v-if="canManage"
      :key="formKey"
      v-model:open="formOpen"
      :supplier="editing"
    />

    <ConfirmDialog
      v-model:open="toggle.open.value"
      :title="
        toggle.target.value?.is_active
          ? t('common.confirmDeactivateTitle', { name: toggle.target.value?.display_name })
          : t('common.confirmActivateTitle', { name: toggle.target.value?.display_name })
      "
      :description="
        toggle.target.value?.is_active
          ? t('suppliers.confirm.deactivateDescription')
          : t('suppliers.confirm.activateDescription')
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
