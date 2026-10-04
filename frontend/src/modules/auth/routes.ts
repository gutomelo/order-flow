import type { RouteRecordRaw } from 'vue-router'

export const authRoutes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'login',
    component: () => import('@/modules/auth/pages/LoginPage.vue'),
    meta: { titleKey: 'auth.login.title', public: true },
  },
]
