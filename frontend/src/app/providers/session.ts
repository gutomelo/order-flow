import type { Pinia } from 'pinia'
import type { Router } from 'vue-router'

import { useSessionStore } from '@/modules/auth/stores/session'
import { configureAuth } from '@/services/http/client'

/** Conecta a sessão ao cliente HTTP (token, refresh automático e expiração). */
export function connectSessionToHttpClient(pinia: Pinia, router: Router): void {
  const session = useSessionStore(pinia)

  configureAuth({
    getAccessToken: () => session.accessToken,
    refreshAccessToken: () => session.refresh(),
    onSessionExpired: () => {
      session.clear()
      const current = router.currentRoute.value
      if (!current.meta.public) {
        void router.replace({ name: 'login', query: { redirect: current.fullPath } })
      }
    },
  })
}
