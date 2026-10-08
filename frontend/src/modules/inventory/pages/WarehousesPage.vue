<script setup lang="ts">
import { CircleCheck, CircleSlash, Pencil, Plus, Warehouse as WarehouseIcon } from '@lucide/vue'
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
import WarehouseFormDialog from '@/modules/inventory/components/WarehouseFormDialog.vue'
import { useSetWarehouseActive, useWarehouses } from '@/modules/inventory/composables/useInventory'
import type { Warehouse } from '@/modules/inventory/types'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()
const canManage = computed(() => session.can('inventory:update'))

const { data, isPending, error, refetch, isFetching } = useWarehouses()

const columns = computed(() => [
  { key: 'code', label: t('inventory.fields.code') },
  { key: 'name', label: t('inventory.fields.name') },
  { key: 'status', label: t('common.status.label') },
  ...(canManage.value
    ? [{ key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const }]
    : []),
])

const formOpen = ref(false)
const editing = ref<Warehouse | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')
function openForm(warehouse: Warehouse | null) {
  editing.value = warehouse
  formOpen.value = true
}

const setActive = useSetWarehouseActive()
const toggle = useActivationToggle<Warehouse>({
  mutate: (input) => setActive.mutateAsync(input),
  successMessage: (w) =>
    t(
      w.is_active
        ? 'inventory.feedback.warehouseDeactivated'
        : 'inventory.feedback.warehouseActivated',
    ),
})
</script>

<template>
  <div>
    <PageHeader
      :title="t('inventory.warehouses.title')"
      :description="t('inventory.warehouses.description')"
    >
      <template v-if="canManage" #actions>
        <BaseButton @click="openForm(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('inventory.actions.createWarehouse') }}
        </BaseButton>
      </template>
    </PageHeader>

    <DataTable
      :caption="t('inventory.warehouses.title')"
      :columns="columns"
      :rows="data"
      :paginated="false"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('inventory.warehouses.errorTitle')"
      :empty-title="t('inventory.warehouses.emptyTitle')"
      :empty-description="t('inventory.warehouses.emptyDescription')"
      :empty-icon="WarehouseIcon"
      min-width="560px"
      @retry="refetch()"
    >
      <template v-if="canManage" #empty-action>
        <BaseButton @click="openForm(null)">{{
          t('inventory.actions.createWarehouse')
        }}</BaseButton>
      </template>
      <template #cell-code="{ row }"
        ><span class="font-mono">{{ row.code }}</span></template
      >
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
            <span class="sr-only">{{ t('common.editItem', { name: row.code }) }}</span>
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
                  ? t('common.deactivateItem', { name: row.code })
                  : t('common.activateItem', { name: row.code })
              }}
            </span>
          </BaseButton>
        </div>
      </template>
    </DataTable>

    <WarehouseFormDialog
      v-if="canManage"
      :key="formKey"
      v-model:open="formOpen"
      :warehouse="editing"
    />

    <ConfirmDialog
      v-model:open="toggle.open.value"
      :title="
        toggle.target.value?.is_active
          ? t('common.confirmDeactivateTitle', { name: toggle.target.value?.code })
          : t('common.confirmActivateTitle', { name: toggle.target.value?.code })
      "
      :description="
        toggle.target.value?.is_active
          ? t('inventory.warehouses.confirmDeactivate')
          : t('inventory.warehouses.confirmActivate')
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
