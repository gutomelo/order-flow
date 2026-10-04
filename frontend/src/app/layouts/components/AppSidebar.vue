<script setup lang="ts">
import { PanelLeftClose, PanelLeftOpen } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import SidebarNav from '@/app/layouts/components/SidebarNav.vue'

const { collapsed } = defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ toggle: [] }>()

const { t } = useI18n()
</script>

<template>
  <aside
    id="app-sidebar"
    class="sticky top-14 h-[calc(100vh-3.5rem)] shrink-0 flex-col justify-between border-r border-border bg-sidebar p-3 transition-[width] duration-200"
    :class="collapsed ? 'w-16' : 'w-64'"
  >
    <SidebarNav :collapsed="collapsed" />

    <button
      type="button"
      class="flex h-9 items-center gap-3 rounded-md px-3 text-sm text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
      aria-controls="app-sidebar"
      :aria-expanded="!collapsed"
      @click="emit('toggle')"
    >
      <component
        :is="collapsed ? PanelLeftOpen : PanelLeftClose"
        class="size-4 shrink-0"
        aria-hidden="true"
      />
      <span :class="{ 'sr-only': collapsed }">
        {{ collapsed ? t('layout.expandSidebar') : t('layout.collapseSidebar') }}
      </span>
    </button>
  </aside>
</template>
