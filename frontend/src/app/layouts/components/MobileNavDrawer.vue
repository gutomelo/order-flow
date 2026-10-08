<script setup lang="ts">
import { X } from '@lucide/vue'
import { useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import AppLogo from '@/app/layouts/components/AppLogo.vue'
import SidebarNav from '@/app/layouts/components/SidebarNav.vue'

const open = defineModel<boolean>('open', { required: true })

const { t } = useI18n()
const dialog = useTemplateRef<HTMLDialogElement>('dialog')

// <dialog> nativo em modo modal: focus trap, Esc e inertização do resto da página sem
// dependências extras.
watch(open, (isOpen) => {
  const element = dialog.value
  if (!element || typeof element.showModal !== 'function') return
  if (isOpen && !element.open) element.showModal()
  if (!isOpen && element.open) element.close()
})

function onBackdropClick(event: MouseEvent) {
  if (event.target === dialog.value) open.value = false
}
</script>

<template>
  <dialog
    ref="dialog"
    class="m-0 h-full max-h-none w-72 max-w-[85vw] bg-sidebar p-0 backdrop:bg-sidebar/60 lg:hidden"
    :aria-label="t('nav.label')"
    @close="open = false"
    @click="onBackdropClick"
  >
    <div class="flex h-full flex-col gap-4 p-3">
      <div class="flex h-10 items-center justify-between px-1">
        <AppLogo inverted />
        <button
          type="button"
          class="inline-flex size-9 items-center justify-center rounded-md text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active"
          :aria-label="t('layout.closeMenu')"
          @click="open = false"
        >
          <X class="size-5" aria-hidden="true" />
        </button>
      </div>
      <SidebarNav />
    </div>
  </dialog>
</template>
