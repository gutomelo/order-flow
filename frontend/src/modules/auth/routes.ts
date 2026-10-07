import type { RouteRecordRaw } from 'vue-router'

export const authRoutes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'login',
    component: () => import('@/modules/auth/pages/LoginPage.vue'),
    meta: { titleKey: 'auth.login.title', public: true },
  },
]

// Senha por e-mail (convite e "esqueci minha senha"): públicas, no mesmo layout do login.
export const forgotPasswordRoutes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'forgot-password',
    component: () => import('@/modules/auth/pages/ForgotPasswordPage.vue'),
    meta: { titleKey: 'auth.forgot.title', public: true },
  },
]

export const resetPasswordRoutes: RouteRecordRaw[] = [
  {
    path: '',
    name: 'reset-password',
    component: () => import('@/modules/auth/pages/ResetPasswordPage.vue'),
    meta: { titleKey: 'auth.reset.title', public: true },
  },
]
