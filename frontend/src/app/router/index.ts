import {
  createRouter,
  createWebHistory,
  type Router,
  type RouteRecordRaw,
  type RouterHistory,
} from 'vue-router'

import AppLayout from '@/app/layouts/AppLayout.vue'
import { i18n } from '@/app/providers/i18n'
import { dashboardRoutes } from '@/modules/dashboard/routes'

declare module 'vue-router' {
  interface RouteMeta {
    /** Chave i18n do título da página (document.title). */
    titleKey?: string
  }
}

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: { name: 'dashboard' } },
      ...dashboardRoutes,
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

  router.afterEach((to) => {
    const appName = i18n.global.t('app.name')
    document.title = to.meta.titleKey ? `${i18n.global.t(to.meta.titleKey)} · ${appName}` : appName
  })

  return router
}
