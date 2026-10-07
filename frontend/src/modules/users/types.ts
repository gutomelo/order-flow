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
  /** Criado por convite e ainda sem senha definida. */
  invitation_pending: boolean
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
  /** `null` = convite por e-mail (a pessoa define a própria senha). */
  password: string | null
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
