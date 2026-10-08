import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '@/modules/auth/api/authApi'
import type { CurrentUser, Permission } from '@/modules/auth/types'

/**
 * Sessão do usuário (client state — ADR-003).
 *
 * O access token vive SOMENTE em memória (nunca em localStorage: um XSS o leria). Ao recarregar
 * a página, `restore()` usa o cookie HttpOnly de refresh para obter um novo token (ADR-007).
 */
export const useSessionStore = defineStore('session', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<CurrentUser | null>(null)
  const restored = ref(false)

  // Várias requisições podem receber 401 ao mesmo tempo: todas aguardam o MESMO refresh.
  // Refreshes paralelos fariam o segundo usar um cookie já rotacionado (e falhar).
  let refreshInFlight: Promise<string | null> | null = null

  const isAuthenticated = computed(() => accessToken.value !== null && user.value !== null)

  function can(permission: Permission | undefined): boolean {
    if (!permission) return true
    return user.value?.permissions.includes(permission) ?? false
  }

  function clear() {
    accessToken.value = null
    user.value = null
  }

  async function login(email: string, password: string) {
    const response = await authApi.login({ email, password })
    accessToken.value = response.access
    user.value = response.user
    restored.value = true
  }

  function refresh(): Promise<string | null> {
    refreshInFlight ??= authApi
      .refreshSession()
      .then((token) => {
        accessToken.value = token
        return token
      })
      .catch(() => {
        clear()
        return null
      })
      .finally(() => {
        refreshInFlight = null
      })
    return refreshInFlight
  }

  /** Tenta reabrir a sessão a partir do cookie de refresh (uma vez por carregamento). */
  async function restore(): Promise<void> {
    if (restored.value) return
    restored.value = true
    const token = await refresh()
    if (!token) return
    try {
      user.value = await authApi.fetchCurrentUser()
    } catch {
      clear()
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      clear()
    }
  }

  return {
    accessToken,
    user,
    restored,
    isAuthenticated,
    can,
    login,
    refresh,
    restore,
    logout,
    clear,
  }
})
