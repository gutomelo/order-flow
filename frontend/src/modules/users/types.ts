import type { Role, TeamSummary } from '@/modules/auth/types'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: Role
  team: TeamSummary | null
  is_active: boolean
  last_login: string | null
  date_joined: string
}

export interface Team {
  id: string
  name: string
  member_count: number
  created_at: string
}

export type UserStatusFilter = '' | 'active' | 'inactive'

export interface UserFilters {
  page: number
  search: string
  role: Role | ''
  status: UserStatusFilter
}

export interface CreateUserInput {
  email: string
  password: string
  first_name: string
  last_name: string
  role: Role
  team_id: string | null
}

export interface UpdateUserInput {
  first_name: string
  last_name: string
  team_id: string | null
}
