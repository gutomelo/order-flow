import {
  Boxes,
  Building2,
  FolderTree,
  History,
  LayoutDashboard,
  Package,
  Tags,
  Truck,
  Users,
  UsersRound,
  Warehouse,
} from '@lucide/vue'
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
  {
    routeName: 'customers',
    labelKey: 'nav.customers',
    icon: Building2,
    permission: 'customers:read',
  },
  {
    routeName: 'customer-segments',
    labelKey: 'nav.segments',
    icon: Tags,
    permission: 'customers:read',
  },
  { routeName: 'products', labelKey: 'nav.products', icon: Package, permission: 'catalog:read' },
  {
    routeName: 'categories',
    labelKey: 'nav.categories',
    icon: FolderTree,
    permission: 'catalog:read',
  },
  { routeName: 'suppliers', labelKey: 'nav.suppliers', icon: Truck, permission: 'suppliers:read' },
  { routeName: 'stock', labelKey: 'nav.stock', icon: Boxes, permission: 'inventory:read' },
  {
    routeName: 'movements',
    labelKey: 'nav.movements',
    icon: History,
    permission: 'inventory:read',
  },
  {
    routeName: 'warehouses',
    labelKey: 'nav.warehouses',
    icon: Warehouse,
    permission: 'inventory:read',
  },
  { routeName: 'users', labelKey: 'nav.users', icon: Users, permission: 'users:manage' },
  { routeName: 'teams', labelKey: 'nav.teams', icon: UsersRound, permission: 'users:manage' },
]
