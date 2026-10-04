import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import { useUiStore } from '@/app/stores/ui'

describe('ui store', () => {
  beforeEach(() => {
    window.localStorage.clear()
    delete document.documentElement.dataset.theme
    setActivePinia(createPinia())
  })

  it('starts expanded and following the system theme', () => {
    const ui = useUiStore()

    expect(ui.sidebarCollapsed).toBe(false)
    expect(ui.theme).toBe('system')
    expect(document.documentElement.dataset.theme).toBeUndefined()
  })

  it('applies an explicit theme to the document root', async () => {
    const ui = useUiStore()

    ui.setTheme('dark')
    await nextTick()
    expect(document.documentElement.dataset.theme).toBe('dark')

    ui.setTheme('system')
    await nextTick()
    expect(document.documentElement.dataset.theme).toBeUndefined()
  })

  it('remembers preferences across sessions', async () => {
    const ui = useUiStore()
    ui.toggleSidebar()
    ui.setTheme('light')
    await nextTick()

    setActivePinia(createPinia())
    const restored = useUiStore()

    expect(restored.sidebarCollapsed).toBe(true)
    expect(restored.theme).toBe('light')
  })

  it('ignores corrupted persisted state', () => {
    window.localStorage.setItem('orderflow:ui', '{not json')

    const ui = useUiStore()

    expect(ui.sidebarCollapsed).toBe(false)
    expect(ui.theme).toBe('system')
  })
})
