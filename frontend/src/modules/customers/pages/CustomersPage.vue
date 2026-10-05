<script setup lang="ts">
import { Building2, CircleCheck, CircleSlash, Plus } from '@lucide/vue'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import BaseButton from '@/components/ui/BaseButton.vue'
import DataTable from '@/components/ui/DataTable.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import SelectField from '@/components/ui/SelectField.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useSessionStore } from '@/modules/auth/stores/session'
import { CUSTOMERS_PAGE_SIZE } from '@/modules/customers/api/customersApi'
import CustomerFormDialog from '@/modules/customers/components/CustomerFormDialog.vue'
import { useCustomersList, useSegmentOptions } from '@/modules/customers/composables/useCustomers'
import type { CustomerFilters, StatusFilter } from '@/modules/customers/types'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canCreate = computed(() => session.can('customers:create'))

const { filters, field, hasActiveFilters } = useUrlFilters<CustomerFilters>(
  { page: 1, search: '', status: '', segment: '' },
  { status: (raw) => (raw === 'active' || raw === 'inactive' ? (raw as StatusFilter) : undefined) },
)
const search = field('search')
const status = field('status')
const segment = field('segment')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useCustomersList(filters)
const segments = useSegmentOptions()

const statusOptions = computed(() => [
  { value: '', label: t('common.allStatuses') },
  { value: 'active', label: t('common.status.active') },
  { value: 'inactive', label: t('common.status.inactive') },
])
const segmentOptions = computed(() => [
  { value: '', label: t('customers.filters.allSegments') },
  ...(segments.data.value ?? []).map((s) => ({
    value: s.id,
    label: s.is_active ? s.name : t('customers.inactiveName', { name: s.name }),
  })),
])
const columns = computed(() => [
  { key: 'name', label: t('customers.fields.name') },
  { key: 'tax_id_formatted', label: t('customers.fields.taxId') },
  { key: 'segment', label: t('customers.fields.segment') },
  { key: 'status', label: t('common.status.label') },
])

const formOpen = ref(false)
</script>

<template>
  <div>
    <PageHeader :title="t('customers.title')" :description="t('customers.description')">
      <template v-if="canCreate" #actions>
        <BaseButton @click="formOpen = true">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('customers.actions.create') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('customers.filters.search')" />
      <SelectField
        v-model="segment"
        :label="t('customers.fields.segment')"
        :options="segmentOptions"
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
      :caption="t('customers.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="CUSTOMERS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('customers.error.title')"
      :empty-title="t('customers.empty.title')"
      :empty-description="t('customers.empty.description')"
      :empty-icon="Building2"
      :filtered="hasActiveFilters"
      @retry="refetch()"
    >
      <template v-if="canCreate" #empty-action>
        <BaseButton @click="formOpen = true">{{ t('customers.actions.create') }}</BaseButton>
      </template>
      <template #cell-name="{ row }">
        <RouterLink
          :to="{ name: 'customer-detail', params: { id: row.id } }"
          class="font-medium text-link underline-offset-2 hover:underline"
        >
          {{ row.display_name }}
        </RouterLink>
        <p v-if="row.trade_name" class="text-xs text-text-secondary">{{ row.legal_name }}</p>
      </template>
      <template #cell-tax_id_formatted="{ row }">
        <span class="tabular-nums">{{ row.tax_id_formatted }}</span>
      </template>
      <template #cell-segment="{ row }">
        <span v-if="row.segment">{{ row.segment.name }}</span>
        <span v-else class="text-text-secondary">{{ t('customers.noSegment') }}</span>
      </template>
      <template #cell-status="{ row }">
        <StatusBadge
          :label="row.is_active ? t('common.status.active') : t('common.status.inactive')"
          :icon="row.is_active ? CircleCheck : CircleSlash"
          :tone="row.is_active ? 'success' : 'neutral'"
        />
      </template>
    </DataTable>

    <CustomerFormDialog v-if="canCreate" v-model:open="formOpen" />
  </div>
</template>
