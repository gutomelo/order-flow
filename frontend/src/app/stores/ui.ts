import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'orderflow:ui'

interface PersistedUiState {
  sidebarCollapsed: boolean
  theme: ThemePreference
}

const DEFAULT_STATE: PersistedUiState = { sidebarCollapsed: false, theme: 'system' }

function isThemePreference(value: unknown): value is ThemePreference {
  return value === 'light' || value === 'dark' || value === 'system'
}

// localStorage pode estar indisponível (modo privado, bloqueio): a UI funciona sem ele.
function readPersisted(): PersistedUiState {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_STATE
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return DEFAULT_STATE
    const candidate = parsed as Partial<PersistedUiState>
    return {
      sidebarCollapsed: candidate.sidebarCollapsed === true,
      theme: isThemePreference(candidate.theme) ? candidate.theme : DEFAULT_STATE.theme,
    }
  } catch {
    return DEFAULT_STATE
  }
}

function writePersisted(state: PersistedUiState): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Preferência apenas não é lembrada.
  }
}

export function applyTheme(theme: ThemePreference, root: HTMLElement = document.documentElement) {
  if (theme === 'system') {
    delete root.dataset.theme
  } else {
    root.dataset.theme = theme
  }
}

/** Estado de UI do cliente (não é server state — ADR-003). */
export const useUiStore = defineStore('ui', () => {
  const initial = readPersisted()
  const sidebarCollapsed = ref(initial.sidebarCollapsed)
  const theme = ref<ThemePreference>(initial.theme)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setTheme(value: ThemePreference) {
    theme.value = value
  }

  watch(theme, (value) => applyTheme(value), { immediate: true })
  watch([sidebarCollapsed, theme], () =>
    writePersisted({ sidebarCollapsed: sidebarCollapsed.value, theme: theme.value }),
  )

  return { sidebarCollapsed, theme, toggleSidebar, setTheme }
})
