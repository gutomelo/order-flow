import type { Role } from '@/modules/auth/types'
import type {
  CreateUserInput,
  Team,
  UpdateUserInput,
  User,
  UserFilters,
} from '@/modules/users/types'
import { http } from '@/services/http/client'
import type { Paginated } from '@/types/api'

export const USERS_PAGE_SIZE = 25

export async function listUsers(filters: UserFilters) {
  const params: Record<string, string | number | boolean> = {
    page: filters.page,
    page_size: USERS_PAGE_SIZE,
  }
  if (filters.search) params.search = filters.search
  if (filters.role) params.role = filters.role
  if (filters.status) params.is_active = filters.status === 'active'
  const { data } = await http.get<Paginated<User>>('/users', { params })
  return data
}

export async function createUser(input: CreateUserInput) {
  const { data } = await http.post<User>('/users', input)
  return data
}

export async function updateUser(id: string, input: UpdateUserInput) {
  const { data } = await http.patch<User>(`/users/${id}`, input)
  return data
}

export async function changeUserRole(id: string, role: Role) {
  const { data } = await http.post<User>(`/users/${id}/change-role`, { role })
  return data
}

export async function setUserActive(id: string, active: boolean) {
  const { data } = await http.post<User>(`/users/${id}/${active ? 'activate' : 'deactivate'}`)
  return data
}

/** Equipes cabem em uma página na prática; busca até 100 para seletores. */
export async function listTeams() {
  const { data } = await http.get<Paginated<Team>>('/teams', { params: { page_size: 100 } })
  return data
}

export async function createTeam(name: string) {
  const { data } = await http.post<Team>('/teams', { name })
  return data
}

export async function renameTeam(id: string, name: string) {
  const { data } = await http.patch<Team>(`/teams/${id}`, { name })
  return data
}
