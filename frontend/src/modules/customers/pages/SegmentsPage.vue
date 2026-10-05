<script setup lang="ts">
import { CircleCheck, CircleSlash, Pencil, Plus, Tags } from '@lucide/vue'
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
import { SEGMENTS_PAGE_SIZE } from '@/modules/customers/api/customersApi'
import SegmentFormDialog from '@/modules/customers/components/SegmentFormDialog.vue'
import { useSegmentsList, useSetSegmentActive } from '@/modules/customers/composables/useCustomers'
import type { Segment, SegmentFilters, StatusFilter } from '@/modules/customers/types'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canManage = computed(() => session.can('customers:manage_segments'))

const { filters, field, hasActiveFilters } = useUrlFilters<SegmentFilters>(
  { page: 1, search: '', status: '' },
  { status: (raw) => (raw === 'active' || raw === 'inactive' ? (raw as StatusFilter) : undefined) },
)
const search = field('search')
const status = field('status')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useSegmentsList(filters)

const statusOptions = computed(() => [
  { value: '', label: t('common.allStatuses') },
  { value: 'active', label: t('common.status.active') },
  { value: 'inactive', label: t('common.status.inactive') },
])
const columns = computed(() => [
  { key: 'code', label: t('segments.fields.code') },
  { key: 'name', label: t('segments.fields.name') },
  { key: 'active_customers', label: t('segments.fields.activeCustomers'), align: 'right' as const },
  { key: 'status', label: t('common.status.label') },
  ...(canManage.value
    ? [{ key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const }]
    : []),
])

const formOpen = ref(false)
const editing = ref<Segment | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')
function openForm(segment: Segment | null) {
  editing.value = segment
  formOpen.value = true
}

const setActive = useSetSegmentActive()
const toggle = useActivationToggle<Segment>({
  mutate: (input) => setActive.mutateAsync(input),
  successMessage: (s) =>
    t(s.is_active ? 'segments.feedback.deactivated' : 'segments.feedback.activated'),
})
</script>

<template>
  <div>
    <PageHeader :title="t('segments.title')" :description="t('segments.description')">
      <template v-if="canManage" #actions>
        <BaseButton @click="openForm(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('segments.actions.create') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('segments.filters.search')" />
      <SelectField
        v-model="status"
        :label="t('common.status.label')"
        :options="statusOptions"
        hide-label
      />
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('segments.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="SEGMENTS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('segments.error.title')"
      :empty-title="t('segments.empty.title')"
      :empty-description="t('segments.empty.description')"
      :empty-icon="Tags"
      :filtered="hasActiveFilters"
      @retry="refetch()"
    >
      <template v-if="canManage" #empty-action>
        <BaseButton @click="openForm(null)">{{ t('segments.actions.create') }}</BaseButton>
      </template>
      <template #cell-code="{ row }">
        <span class="font-mono">{{ row.code }}</span>
      </template>
      <template #cell-name="{ row }">
        <p class="font-medium">{{ row.name }}</p>
        <p v-if="row.description" class="text-xs text-text-secondary">{{ row.description }}</p>
      </template>
      <template #cell-active_customers="{ row }">
        <RouterLink
          :to="{ name: 'customers', query: { segment: row.id } }"
          class="tabular-nums text-link underline-offset-2 hover:underline"
        >
          {{ row.active_customers }}
          <span class="sr-only">{{ t('segments.viewCustomers', { name: row.name }) }}</span>
        </RouterLink>
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

    <SegmentFormDialog v-if="canManage" :key="formKey" v-model:open="formOpen" :segment="editing" />

    <ConfirmDialog
      v-model:open="toggle.open.value"
      :title="
        toggle.target.value?.is_active
          ? t('common.confirmDeactivateTitle', { name: toggle.target.value?.name })
          : t('common.confirmActivateTitle', { name: toggle.target.value?.name })
      "
      :description="
        toggle.target.value?.is_active
          ? t('segments.confirm.deactivateDescription')
          : t('segments.confirm.activateDescription')
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
