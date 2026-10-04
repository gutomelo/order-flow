<script setup lang="ts">
import { ChevronDown, LogOut } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref, useId, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import { useSessionStore } from '@/modules/auth/stores/session'

// Padrão "disclosure" (WAI-ARIA APG): botão com aria-expanded controlando um painel.
const { t } = useI18n()
const router = useRouter()
const session = useSessionStore()

const open = ref(false)
const loggingOut = ref(false)
const root = useTemplateRef<HTMLElement>('root')
const panelId = useId()

const initials = computed(() => {
  const user = session.user
  if (!user) return ''
  const source = `${user.first_name} ${user.last_name}`.trim() || user.email
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
})

function onDocumentClick(event: MouseEvent) {
  if (open.value && root.value && !root.value.contains(event.target as Node)) open.value = false
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') open.value = false
}

onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))

async function logout() {
  loggingOut.value = true
  try {
    await session.logout()
  } finally {
    loggingOut.value = false
    open.value = false
    await router.replace({ name: 'login' })
  }
}
</script>

<template>
  <div v-if="session.user" ref="root" class="relative" @keydown="onKeydown">
    <button
      type="button"
      class="flex items-center gap-2 rounded-md px-1.5 py-1 text-sm hover:bg-surface-muted"
      :aria-expanded="open"
      :aria-controls="panelId"
      @click="open = !open"
    >
      <span
        class="flex size-7 items-center justify-center rounded-full bg-primary-subtle text-xs font-semibold text-text-primary"
        aria-hidden="true"
      >
        {{ initials }}
      </span>
      <span class="hidden font-medium text-text-primary sm:inline">
        {{ session.user.full_name }}
      </span>
      <span class="sr-only sm:hidden">{{ t('userMenu.label') }}</span>
      <ChevronDown class="size-4 text-text-secondary" aria-hidden="true" />
    </button>

    <div
      v-show="open"
      :id="panelId"
      class="absolute right-0 z-40 mt-2 w-64 rounded-lg border border-border bg-surface p-1 shadow-lg"
    >
      <div class="px-3 py-2">
        <p class="truncate text-sm font-medium text-text-primary">{{ session.user.full_name }}</p>
        <p class="truncate text-xs text-text-secondary">{{ session.user.email }}</p>
        <p class="mt-2 text-xs text-text-secondary">
          {{ session.user.organization.name }} · {{ t(`roles.${session.user.role}`) }}
        </p>
      </div>
      <div class="my-1 h-px bg-border" />
      <button
        type="button"
        class="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-text-primary hover:bg-surface-muted disabled:opacity-60"
        :disabled="loggingOut"
        @click="logout"
      >
        <LogOut class="size-4 text-text-secondary" aria-hidden="true" />
        {{ t('userMenu.logout') }}
      </button>
    </div>
  </div>
</template>
