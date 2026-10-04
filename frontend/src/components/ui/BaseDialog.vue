<script setup lang="ts">
import { X } from '@lucide/vue'
import { onMounted, useId, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * Diálogo modal sobre <dialog> nativo: focus trap, Esc, `inert` no restante da página e retorno
 * do foco ao elemento de origem são feitos pelo navegador.
 */
const open = defineModel<boolean>('open', { required: true })
const { title, description } = defineProps<{ title: string; description?: string }>()

const { t } = useI18n()
const dialog = useTemplateRef<HTMLDialogElement>('dialog')
const titleId = useId()
const descriptionId = useId()

function sync(isOpen: boolean) {
  const element = dialog.value
  if (!element || typeof element.showModal !== 'function') return
  if (isOpen && !element.open) element.showModal()
  if (!isOpen && element.open) element.close()
}

// O diálogo pode ser montado já aberto (ex.: recriado via `key`).
onMounted(() => sync(open.value))
watch(open, sync, { flush: 'post' })

function onBackdropClick(event: MouseEvent) {
  if (event.target === dialog.value) open.value = false
}
</script>

<template>
  <dialog
    ref="dialog"
    class="m-auto w-[calc(100%-2rem)] max-w-lg rounded-lg border border-border bg-surface p-0 text-text-primary backdrop:bg-sidebar/60"
    :aria-labelledby="titleId"
    :aria-describedby="description ? descriptionId : undefined"
    @close="open = false"
    @click="onBackdropClick"
  >
    <div v-if="open" class="flex flex-col gap-5 p-6">
      <header class="flex items-start justify-between gap-4">
        <div>
          <h2 :id="titleId" class="text-lg font-semibold">{{ title }}</h2>
          <p v-if="description" :id="descriptionId" class="mt-1 text-sm text-text-secondary">
            {{ description }}
          </p>
        </div>
        <button
          type="button"
          class="-m-1 inline-flex size-8 items-center justify-center rounded-md text-text-secondary hover:bg-surface-muted hover:text-text-primary"
          :aria-label="t('common.close')"
          @click="open = false"
        >
          <X class="size-4" aria-hidden="true" />
        </button>
      </header>
      <slot />
      <footer v-if="$slots.footer" class="flex flex-wrap justify-end gap-2">
        <slot name="footer" />
      </footer>
    </div>
  </dialog>
</template>
