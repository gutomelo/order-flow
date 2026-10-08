<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { primaryNavigation } from '@/app/navigation'
import { useSessionStore } from '@/modules/auth/stores/session'

const { collapsed = false } = defineProps<{ collapsed?: boolean }>()

const { t } = useI18n()
const session = useSessionStore()
const items = computed(() => primaryNavigation.filter((item) => session.can(item.permission)))
</script>

<template>
  <nav :aria-label="t('nav.label')">
    <ul class="flex flex-col gap-1">
      <li v-for="item in items" :key="item.routeName">
        <RouterLink
          :to="{ name: item.routeName }"
          class="flex h-9 items-center gap-3 rounded-md border-l-2 border-transparent px-3 text-sm font-medium text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active [&.router-link-active]:border-primary [&.router-link-active]:bg-sidebar-hover [&.router-link-active]:text-sidebar-text-active"
          :title="collapsed ? t(item.labelKey) : undefined"
        >
          <component :is="item.icon" class="size-4 shrink-0" aria-hidden="true" />
          <span :class="{ 'sr-only': collapsed }">{{ t(item.labelKey) }}</span>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>
