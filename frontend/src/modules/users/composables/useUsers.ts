import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import type { Role } from '@/modules/auth/types'
import * as usersApi from '@/modules/users/api/usersApi'
import type { CreateUserInput, UpdateUserInput, UserFilters } from '@/modules/users/types'

export const usersKeys = {
  all: ['users'] as const,
  lists: () => [...usersKeys.all, 'list'] as const,
  list: (filters: UserFilters) => [...usersKeys.lists(), filters] as const,
}

export const teamsKeys = {
  all: ['teams'] as const,
  list: () => [...teamsKeys.all, 'list'] as const,
}

export function useUsersList(filters: MaybeRefOrGetter<UserFilters>) {
  return useQuery({
    queryKey: computed(() => usersKeys.list(toValue(filters))),
    queryFn: () => usersApi.listUsers(toValue(filters)),
    // Mantém a página anterior visível enquanto a próxima carrega (sem "piscar" a tabela).
    placeholderData: keepPreviousData,
  })
}

export function useTeamsList() {
  return useQuery({ queryKey: teamsKeys.list(), queryFn: usersApi.listTeams })
}

/** Mutations de usuários invalidam usuários e equipes (contagem de membros). */
function useInvalidateIdentity() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: usersKeys.all }),
      queryClient.invalidateQueries({ queryKey: teamsKeys.all }),
    ])
}

export function useCreateUser() {
  const invalidate = useInvalidateIdentity()
  return useMutation({
    mutationFn: (input: CreateUserInput) => usersApi.createUser(input),
    onSuccess: invalidate,
  })
}

export function useUpdateUser() {
  const invalidate = useInvalidateIdentity()
  return useMutation({
    mutationFn: async (input: { id: string; profile: UpdateUserInput; role?: Role }) => {
      const user = await usersApi.updateUser(input.id, input.profile)
      // Papel tem endpoint próprio (regras de último ADMIN e registro de alteração).
      return input.role && input.role !== user.role
        ? usersApi.changeUserRole(input.id, input.role)
        : user
    },
    onSettled: invalidate,
  })
}

export function useResendInvitation() {
  const invalidate = useInvalidateIdentity()
  return useMutation({
    mutationFn: (id: string) => usersApi.resendInvitation(id),
    onSuccess: invalidate,
  })
}

export function useSetUserActive() {
  const invalidate = useInvalidateIdentity()
  return useMutation({
    mutationFn: (input: { id: string; active: boolean }) =>
      usersApi.setUserActive(input.id, input.active),
    onSuccess: invalidate,
  })
}

export function useSaveTeam() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { id?: string; name: string }) =>
      input.id ? usersApi.renameTeam(input.id, input.name) : usersApi.createTeam(input.name),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: teamsKeys.all }),
  })
}
