import { LayoutDashboard } from '@lucide/vue'
import type { Component } from 'vue'

export interface NavigationItem {
  /** Nome da rota (vue-router). */
  routeName: string
  /** Chave i18n do rótulo. */
  labelKey: string
  icon: Component
}

// Itens entram aqui junto com as features (orders, inventory, products...). Na Phase 2, cada
// item passa a declarar a permissão necessária para ser exibido.
export const primaryNavigation: NavigationItem[] = [
  { routeName: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard },
]
