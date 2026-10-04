<script setup lang="ts">
import { nextTick, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'

import AppSidebar from '@/app/layouts/components/AppSidebar.vue'
import AppTopbar from '@/app/layouts/components/AppTopbar.vue'
import MobileNavDrawer from '@/app/layouts/components/MobileNavDrawer.vue'
import { useUiStore } from '@/app/stores/ui'

const { t } = useI18n()
const ui = useUiStore()
const route = useRoute()

const mobileNavOpen = ref(false)
const main = useTemplateRef<HTMLElement>('main')

// Após uma navegação: fecha o drawer e move o foco para o conteúdo, para que leitores de tela
// anunciem a nova página (em SPAs o navegador não faz isso sozinho).
watch(
  () => route.fullPath,
  async (_current, previous) => {
    mobileNavOpen.value = false
    if (previous !== undefined) {
      await nextTick()
      main.value?.focus()
    }
  },
)
</script>

<template>
  <div class="min-h-screen bg-background">
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-text-primary"
    >
      {{ t('layout.skipToContent') }}
    </a>

    <AppTopbar @open-menu="mobileNavOpen = true" />

    <div class="flex">
      <AppSidebar
        class="hidden lg:flex"
        :collapsed="ui.sidebarCollapsed"
        @toggle="ui.toggleSidebar()"
      />

      <main
        id="main-content"
        ref="main"
        tabindex="-1"
        class="min-w-0 flex-1 px-4 py-6 focus:outline-none sm:px-6 lg:px-8"
      >
        <RouterView />
      </main>
    </div>

    <MobileNavDrawer v-model:open="mobileNavOpen" />
  </div>
</template>
