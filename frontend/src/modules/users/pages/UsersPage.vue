<script setup lang="ts">
import { CircleCheck, CircleSlash, Pencil, Plus, Search, UserX, Users } from '@lucide/vue'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { useToastStore } from '@/app/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SelectField from '@/components/ui/SelectField.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TablePagination from '@/components/ui/TablePagination.vue'
import { useApiErrorMessage } from '@/composables/useApiErrorMessage'
import { useSessionStore } from '@/modules/auth/stores/session'
import { ROLES, type Role } from '@/modules/auth/types'
import { USERS_PAGE_SIZE } from '@/modules/users/api/usersApi'
import UserFormDialog from '@/modules/users/components/UserFormDialog.vue'
import { useSetUserActive, useUsersList } from '@/modules/users/composables/useUsers'
import type { User, UserFilters, UserStatusFilter } from '@/modules/users/types'
import { formatDateTime } from '@/utils/datetime'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const toasts = useToastStore()
const errorMessage = useApiErrorMessage()

// Filtros vivem na URL: compartilháveis e preservados ao voltar no navegador.
function readFilters(): UserFilters {
  const query = route.query
  const role =
    typeof query.role === 'string' && ROLES.includes(query.role as Role) ? query.role : ''
  const status = query.status === 'active' || query.status === 'inactive' ? query.status : ''
  return {
    page: Math.max(1, Number(query.page) || 1),
    search: typeof query.search === 'string' ? query.search : '',
    role: role as Role | '',
    status: status as UserStatusFilter,
  }
}

const filters = computed(readFilters)
const searchInput = ref(filters.value.search)

function updateFilters(patch: Partial<UserFilters>) {
  const next = { ...filters.value, page: 1, ...patch }
  void router.replace({
    query: {
      ...(next.search ? { search: next.search } : {}),
      ...(next.role ? { role: next.role } : {}),
      ...(next.status ? { status: next.status } : {}),
      ...(next.page > 1 ? { page: String(next.page) } : {}),
    },
  })
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(searchInput, (value) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => updateFilters({ search: value.trim() }), 300)
})

const roleFilter = computed({
  get: () => filters.value.role,
  set: (role: string) => updateFilters({ role: role as Role | '' }),
})
const statusFilter = computed({
  get: () => filters.value.status,
  set: (status: string) => updateFilters({ status: status as UserStatusFilter }),
})
const page = computed({
  get: () => filters.value.page,
  set: (value: number) => updateFilters({ page: value }),
})

const { data, isPending, isError, error, refetch, isFetching } = useUsersList(filters)
const hasFilters = computed(() =>
  Boolean(filters.value.search || filters.value.role || filters.value.status),
)

const roleOptions = computed(() => [
  { value: '', label: t('users.filters.allRoles') },
  ...ROLES.map((role) => ({ value: role, label: t(`roles.${role}`) })),
])
const statusOptions = computed(() => [
  { value: '', label: t('users.filters.allStatuses') },
  { value: 'active', label: t('users.status.active') },
  { value: 'inactive', label: t('users.status.inactive') },
])

// Diálogo de criação/edição: a key recria o componente ao trocar de modo ou usuário.
const formOpen = ref(false)
const editing = ref<User | null>(null)
const formKey = computed(() => editing.value?.id ?? 'new')

function openCreate() {
  editing.value = null
  formOpen.value = true
}
function openEdit(user: User) {
  editing.value = user
  formOpen.value = true
}

// Ativação/desativação com confirmação.
const statusTarget = ref<User | null>(null)
const confirmOpen = ref(false)
const setActive = useSetUserActive()

function askToggleStatus(user: User) {
  statusTarget.value = user
  confirmOpen.value = true
}

async function confirmToggleStatus() {
  const user = statusTarget.value
  if (!user) return
  try {
    await setActive.mutateAsync({ id: user.id, active: !user.is_active })
    toasts.success(t(user.is_active ? 'users.feedback.deactivated' : 'users.feedback.activated'))
    confirmOpen.value = false
  } catch (err) {
    toasts.error(errorMessage(err))
  }
}

const isSelf = (user: User) => user.id === session.user?.id
</script>

<template>
  <div>
    <PageHeader :title="t('users.title')" :description="t('users.description')">
      <template #actions>
        <BaseButton @click="openCreate">
          <Plus class="size-4" aria-hidden="true" />
          {{ t('users.actions.create') }}
        </BaseButton>
      </template>
    </PageHeader>

    <div class="mb-4 flex flex-wrap items-end gap-3">
      <div class="relative min-w-56 flex-1">
        <label for="users-search" class="sr-only">{{ t('users.filters.search') }}</label>
        <Search
          class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-text-secondary"
          aria-hidden="true"
        />
        <input
          id="users-search"
          v-model="searchInput"
          type="search"
          :placeholder="t('users.filters.search')"
          class="h-9 w-full rounded-md border border-border bg-surface pr-3 pl-9 text-sm text-text-primary placeholder:text-text-secondary"
        />
      </div>
      <SelectField
        v-model="roleFilter"
        :label="t('users.fields.role')"
        :options="roleOptions"
        hide-label
      />
      <SelectField
        v-model="statusFilter"
        :label="t('users.fields.status')"
        :options="statusOptions"
        hide-label
      />
    </div>

    <!-- Loading -->
    <div
      v-if="isPending"
      class="space-y-2 rounded-lg border border-border bg-surface p-4"
      role="status"
    >
      <span class="sr-only">{{ t('common.loading') }}</span>
      <div v-for="index in 5" :key="index" class="h-9 animate-pulse rounded bg-surface-muted" />
    </div>

    <!-- Erro -->
    <EmptyState
      v-else-if="isError"
      :title="t('users.error.title')"
      :description="errorMessage(error)"
      :icon="CircleSlash"
      role="alert"
    >
      <template #action>
        <BaseButton variant="secondary" :loading="isFetching" @click="refetch()">
          {{ t('common.retry') }}
        </BaseButton>
      </template>
    </EmptyState>

    <!-- Vazio -->
    <EmptyState
      v-else-if="data && data.results.length === 0"
      :title="hasFilters ? t('users.empty.filteredTitle') : t('users.empty.title')"
      :description="
        hasFilters ? t('users.empty.filteredDescription') : t('users.empty.description')
      "
      :icon="Users"
    />

    <!-- Tabela -->
    <div v-else-if="data" class="rounded-lg border border-border bg-surface">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[720px] text-left text-sm" :aria-busy="isFetching">
          <caption class="sr-only">
            {{
              t('users.title')
            }}
          </caption>
          <thead class="border-b border-border text-xs font-medium text-text-secondary">
            <tr>
              <th scope="col" class="px-4 py-3">{{ t('users.fields.name') }}</th>
              <th scope="col" class="px-4 py-3">{{ t('users.fields.role') }}</th>
              <th scope="col" class="px-4 py-3">{{ t('users.fields.team') }}</th>
              <th scope="col" class="px-4 py-3">{{ t('users.fields.status') }}</th>
              <th scope="col" class="px-4 py-3">{{ t('users.fields.lastLogin') }}</th>
              <th scope="col" class="px-4 py-3 text-right">
                <span class="sr-only">{{ t('common.actions') }}</span>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr v-for="user in data.results" :key="user.id" class="hover:bg-surface-muted/50">
              <td class="px-4 py-3">
                <p class="font-medium text-text-primary">
                  {{ user.full_name }}
                  <span v-if="isSelf(user)" class="text-xs font-normal text-text-secondary">
                    ({{ t('users.you') }})
                  </span>
                </p>
                <p class="text-xs text-text-secondary">{{ user.email }}</p>
              </td>
              <td class="px-4 py-3 text-text-primary">{{ t(`roles.${user.role}`) }}</td>
              <td class="px-4 py-3 text-text-primary">{{ user.team?.name ?? '—' }}</td>
              <td class="px-4 py-3">
                <StatusBadge
                  :label="user.is_active ? t('users.status.active') : t('users.status.inactive')"
                  :icon="user.is_active ? CircleCheck : CircleSlash"
                  :tone="user.is_active ? 'success' : 'neutral'"
                />
              </td>
              <td class="px-4 py-3 text-text-secondary tabular-nums">
                {{ user.last_login ? formatDateTime(user.last_login) : t('users.neverLoggedIn') }}
              </td>
              <td class="px-4 py-3">
                <div class="flex justify-end gap-1">
                  <BaseButton variant="ghost" size="sm" @click="openEdit(user)">
                    <Pencil class="size-4" aria-hidden="true" />
                    <span class="sr-only">{{
                      t('users.actions.editUser', { name: user.full_name })
                    }}</span>
                  </BaseButton>
                  <BaseButton
                    v-if="!isSelf(user)"
                    variant="ghost"
                    size="sm"
                    @click="askToggleStatus(user)"
                  >
                    <component
                      :is="user.is_active ? UserX : CircleCheck"
                      class="size-4"
                      aria-hidden="true"
                    />
                    <span class="sr-only">
                      {{
                        user.is_active
                          ? t('users.actions.deactivateUser', { name: user.full_name })
                          : t('users.actions.activateUser', { name: user.full_name })
                      }}
                    </span>
                  </BaseButton>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="border-t border-border px-4 py-3">
        <TablePagination v-model:page="page" :count="data.count" :page-size="USERS_PAGE_SIZE" />
      </div>
    </div>

    <UserFormDialog :key="formKey" v-model:open="formOpen" :user="editing" />

    <ConfirmDialog
      v-model:open="confirmOpen"
      :title="
        statusTarget?.is_active
          ? t('users.confirm.deactivateTitle', { name: statusTarget?.full_name })
          : t('users.confirm.activateTitle', { name: statusTarget?.full_name })
      "
      :description="
        statusTarget?.is_active
          ? t('users.confirm.deactivateDescription')
          : t('users.confirm.activateDescription')
      "
      :confirm-label="
        statusTarget?.is_active ? t('users.actions.deactivate') : t('users.actions.activate')
      "
      :tone="statusTarget?.is_active ? 'danger' : 'primary'"
      :loading="setActive.isPending.value"
      @confirm="confirmToggleStatus"
    />
  </div>
</template>
