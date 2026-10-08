<script setup lang="ts">
import { Menu } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import AppLogo from '@/app/layouts/components/AppLogo.vue'
import ThemeSwitcher from '@/app/layouts/components/ThemeSwitcher.vue'
import UserMenu from '@/app/layouts/components/UserMenu.vue'

const emit = defineEmits<{ 'open-menu': [] }>()

const { t } = useI18n()
</script>

<template>
  <header
    class="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-surface px-4 sm:px-6"
  >
    <button
      type="button"
      class="-ml-2 inline-flex size-9 items-center justify-center rounded-md text-text-secondary hover:bg-surface-muted hover:text-text-primary lg:hidden"
      :aria-label="t('layout.openMenu')"
      @click="emit('open-menu')"
    >
      <Menu class="size-5" aria-hidden="true" />
    </button>

    <RouterLink :to="{ name: 'dashboard' }" class="rounded-md">
      <AppLogo />
    </RouterLink>

    <div class="ml-auto flex items-center gap-2">
      <ThemeSwitcher />
      <UserMenu />
    </div>
  </header>
</template>
