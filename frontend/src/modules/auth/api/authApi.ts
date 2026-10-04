import type { CurrentUser, LoginResponse } from '@/modules/auth/types'
import { http } from '@/services/http/client'

export async function login(credentials: { email: string; password: string }) {
  const { data } = await http.post<LoginResponse>('/auth/login', credentials)
  return data
}

/** O refresh token vai no cookie HttpOnly; o corpo só traz o novo access token. */
export async function refreshSession() {
  const { data } = await http.post<{ access: string }>('/auth/refresh')
  return data.access
}

export async function logout() {
  await http.post('/auth/logout')
}

export async function fetchCurrentUser() {
  const { data } = await http.get<CurrentUser>('/auth/me')
  return data
}
