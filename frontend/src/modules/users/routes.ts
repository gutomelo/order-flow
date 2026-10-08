import type { RouteRecordRaw } from 'vue-router'

export const usersRoutes: RouteRecordRaw[] = [
  {
    path: 'users',
    name: 'users',
    component: () => import('@/modules/users/pages/UsersPage.vue'),
    meta: { titleKey: 'users.title', permission: 'users:manage' },
  },
  {
    path: 'teams',
    name: 'teams',
    component: () => import('@/modules/users/pages/TeamsPage.vue'),
    meta: { titleKey: 'teams.title', permission: 'users:manage' },
  },
]
