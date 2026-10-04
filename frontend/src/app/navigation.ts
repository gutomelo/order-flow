import { LayoutDashboard, Users, UsersRound } from '@lucide/vue'
import type { Component } from 'vue'

export interface NavigationItem {
  /** Nome da rota (vue-router). */
  routeName: string
  /** Chave i18n do rótulo. */
  labelKey: string
  icon: Component
  /** Itens sem a permissão do usuário ficam ocultos (UX; o backend é a autoridade). */
  permission?: string
}

export const primaryNavigation: NavigationItem[] = [
  { routeName: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard },
  { routeName: 'users', labelKey: 'nav.users', icon: Users, permission: 'users:manage' },
  { routeName: 'teams', labelKey: 'nav.teams', icon: UsersRound, permission: 'users:manage' },
]
