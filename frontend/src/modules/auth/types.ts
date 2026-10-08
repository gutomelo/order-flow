export const ROLES = ['ADMIN', 'MANAGER', 'SALES', 'WAREHOUSE', 'FINANCE', 'VIEWER'] as const
export type Role = (typeof ROLES)[number]

/** Permissão no formato `resource:action` (catálogo oficial no backend: identity.domain). */
export type Permission = string

export interface TeamSummary {
  id: string
  name: string
}

export interface OrganizationSummary {
  id: string
  name: string
  slug: string
}

export interface CurrentUser {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: Role
  team: TeamSummary | null
  organization: OrganizationSummary
  permissions: Permission[]
}

export interface LoginResponse {
  access: string
  user: CurrentUser
}
