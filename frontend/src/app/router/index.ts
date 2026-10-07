import {
  createRouter,
  createWebHistory,
  type Router,
  type RouteRecordRaw,
  type RouterHistory,
} from 'vue-router'

import AppLayout from '@/app/layouts/AppLayout.vue'
import AuthLayout from '@/app/layouts/AuthLayout.vue'
import { i18n } from '@/app/providers/i18n'
import { authRoutes, forgotPasswordRoutes, resetPasswordRoutes } from '@/modules/auth/routes'
import { catalogRoutes } from '@/modules/catalog/routes'
import { useSessionStore } from '@/modules/auth/stores/session'
import { customersRoutes } from '@/modules/customers/routes'
import { dashboardRoutes } from '@/modules/dashboard/routes'
import { inventoryRoutes } from '@/modules/inventory/routes'
import { ordersRoutes } from '@/modules/orders/routes'
import { paymentsRoutes } from '@/modules/payments/routes'
import { pricingRoutes } from '@/modules/pricing/routes'
import { suppliersRoutes } from '@/modules/suppliers/routes'
import { usersRoutes } from '@/modules/users/routes'

declare module 'vue-router' {
  interface RouteMeta {
    /** Chave i18n do título da página (document.title). */
    titleKey?: string
    /** Rota acessível sem sessão (ex.: login). */
    public?: boolean
    /** Permissão exigida (UX: o backend continua sendo a autoridade). */
    permission?: string
  }
}

export const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    component: AuthLayout,
    children: authRoutes,
  },
  { path: '/forgot-password', component: AuthLayout, children: forgotPasswordRoutes },
  { path: '/reset-password', component: AuthLayout, children: resetPasswordRoutes },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: { name: 'dashboard' } },
      ...dashboardRoutes,
      ...ordersRoutes,
      ...paymentsRoutes,
      ...pricingRoutes,
      ...customersRoutes,
      ...catalogRoutes,
      ...suppliersRoutes,
      ...inventoryRoutes,
      ...usersRoutes,
      {
        path: 'forbidden',
        name: 'forbidden',
        component: () => import('@/app/pages/ForbiddenPage.vue'),
        meta: { titleKey: 'forbidden.title' },
      },
      {
        path: ':pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/app/pages/NotFoundPage.vue'),
        meta: { titleKey: 'notFound.title' },
      },
    ],
  },
]

export function createAppRouter(
  history: RouterHistory = createWebHistory(import.meta.env.BASE_URL),
): Router {
  const router = createRouter({ history, routes })

  router.beforeEach(async (to) => {
    const session = useSessionStore()
    // Primeira navegação após carregar a página: tenta reabrir a sessão pelo cookie de refresh.
    await session.restore()

    if (to.meta.public) {
      return session.isAuthenticated && to.name === 'login' ? { name: 'dashboard' } : true
    }
    if (!session.isAuthenticated) {
      return { name: 'login', query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
    }
    if (!session.can(to.meta.permission)) {
      return { name: 'forbidden' }
    }
    return true
  })

  router.afterEach((to) => {
    const appName = i18n.global.t('app.name')
    document.title = to.meta.titleKey ? `${i18n.global.t(to.meta.titleKey)} · ${appName}` : appName
  })

  return router
}
