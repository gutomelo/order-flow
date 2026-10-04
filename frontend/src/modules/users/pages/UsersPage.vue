<script setup lang="ts">
import { CircleCheck, CircleSlash, Pencil, Plus, UserX, Users } from '@lucide/vue'
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
import { ROLES, type Role } from '@/modules/auth/types'
import { USERS_PAGE_SIZE } from '@/modules/users/api/usersApi'
import UserFormDialog from '@/modules/users/components/UserFormDialog.vue'
import { useSetUserActive, useUsersList } from '@/modules/users/composables/useUsers'
import type { User, UserFilters, UserStatusFilter } from '@/modules/users/types'
import { formatDateTime } from '@/utils/datetime'

const { t } = useI18n()
const session = useSessionStore()
const errorMessage = useApiErrorMessage()

const { filters, field, hasActiveFilters } = useUrlFilters<UserFilters>(
  { page: 1, search: '', role: '', status: '' },
  {
    role: (raw) => (ROLES.includes(raw as Role) ? (raw as Role) : undefined),
    status: (raw) =>
      raw === 'active' || raw === 'inactive' ? (raw as UserStatusFilter) : undefined,
  },
)
const search = field('search')
const role = field('role')
const status = field('status')
const page = field('page')

const { data, isPending, error, refetch, isFetching } = useUsersList(filters)

const roleOptions = computed(() => [
  { value: '', label: t('users.filters.allRoles') },
  ...ROLES.map((value) => ({ value, label: t(`roles.${value}`) })),
])
const statusOptions = computed(() => [
  { value: '', label: t('users.filters.allStatuses') },
  { value: 'active', label: t('users.status.active') },
  { value: 'inactive', label: t('users.status.inactive') },
])
const columns = computed(() => [
  { key: 'name', label: t('users.fields.name') },
  { key: 'role', label: t('users.fields.role') },
  { key: 'team', label: t('users.fields.team') },
  { key: 'status', label: t('users.fields.status') },
  { key: 'last_login', label: t('users.fields.lastLogin') },
  { key: 'actions', label: t('common.actions'), srOnly: true, align: 'right' as const },
])

// Diálogo de criação/edição: a key recria o componente ao trocar de modo ou usuário.
const formOpen = ref(false)
const editing = ref<User | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')

function openForm(user: User | null) {
  editing.value = user
  formOpen.value = true
}

const setActive = useSetUserActive()
const toggle = useActivationToggle<User>({
  mutate: (input) => setActive.mutateAsync(input),
  successMessage: (user) =>
    t(user.is_active ? 'users.feedback.deactivated' : 'users.feedback.activated'),
})

const isSelf = (user: User) => user.id === session.user?.id
</script>

<template>
  <div>
    <PageHeader :title="t('users.title')" :description="t('users.description')">
      <template #actions>
        <BaseButton @click="openForm(null)">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('users.actions.create') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <SearchInput v-model="search" :label="t('users.filters.search')" />
      <SelectField
        v-model="role"
        :label="t('users.fields.role')"
        :options="roleOptions"
        hide-label
      />
      <SelectField
        v-model="status"
        :label="t('users.fields.status')"
        :options="statusOptions"
        hide-label
      />
    </div>

    <DataTable
      v-model:page="page"
      :caption="t('users.title')"
      :columns="columns"
      :rows="data?.results"
      :count="data?.count"
      :page-size="USERS_PAGE_SIZE"
      :pending="isPending"
      :fetching="isFetching"
      :error="error ? errorMessage(error) : null"
      :error-title="t('users.error.title')"
      :empty-title="t('users.empty.title')"
      :empty-description="t('users.empty.description')"
      :empty-icon="Users"
      :filtered="hasActiveFilters"
      :filtered-title="t('users.empty.filteredTitle')"
      :filtered-description="t('users.empty.filteredDescription')"
      @retry="refetch()"
    >
      <template #cell-name="{ row }">
        <p class="font-medium">
          {{ row.full_name }}
          <span v-if="isSelf(row)" class="text-xs font-normal text-text-secondary">
            ({{ t('users.you') }})
          </span>
        </p>
        <p class="text-xs text-text-secondary">{{ row.email }}</p>
      </template>
      <template #cell-role="{ row }">{{ t(`roles.${row.role}`) }}</template>
      <template #cell-team="{ row }">{{ row.team?.name ?? '—' }}</template>
      <template #cell-status="{ row }">
        <StatusBadge
          :label="row.is_active ? t('users.status.active') : t('users.status.inactive')"
          :icon="row.is_active ? CircleCheck : CircleSlash"
          :tone="row.is_active ? 'success' : 'neutral'"
        />
      </template>
      <template #cell-last_login="{ row }">
        <span class="text-text-secondary tabular-nums">
          {{ row.last_login ? formatDateTime(row.last_login) : t('users.neverLoggedIn') }}
        </span>
      </template>
      <template #cell-actions="{ row }">
        <div class="flex justify-end gap-1">
          <BaseButton variant="ghost" size="sm" @click="openForm(row)">
            <Pencil class="size-4" aria-hidden="true" />
            <span class="sr-only">{{ t('users.actions.editUser', { name: row.full_name }) }}</span>
          </BaseButton>
          <BaseButton v-if="!isSelf(row)" variant="ghost" size="sm" @click="toggle.ask(row)">
            <component
              :is="row.is_active ? UserX : CircleCheck"
              class="size-4"
              aria-hidden="true"
            />
            <span class="sr-only">
              {{
                row.is_active
                  ? t('users.actions.deactivateUser', { name: row.full_name })
                  : t('users.actions.activateUser', { name: row.full_name })
              }}
            </span>
          </BaseButton>
        </div>
      </template>
    </DataTable>

    <UserFormDialog :key="formKey" v-model:open="formOpen" :user="editing" />

    <ConfirmDialog
      v-model:open="toggle.open.value"
      :title="
        toggle.target.value?.is_active
          ? t('users.confirm.deactivateTitle', { name: toggle.target.value?.full_name })
          : t('users.confirm.activateTitle', { name: toggle.target.value?.full_name })
      "
      :description="
        toggle.target.value?.is_active
          ? t('users.confirm.deactivateDescription')
          : t('users.confirm.activateDescription')
      "
      :confirm-label="
        toggle.target.value?.is_active ? t('users.actions.deactivate') : t('users.actions.activate')
      "
      :tone="toggle.target.value?.is_active ? 'danger' : 'primary'"
      :loading="toggle.running.value"
      :error="toggle.error.value"
      @confirm="toggle.confirm"
    />
  </div>
</template>
