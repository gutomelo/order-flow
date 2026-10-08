import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import * as api from '@/modules/customers/api/customersApi'
import type {
  AddressInput,
  AddressRole,
  ContactInput,
  CustomerFilters,
  CustomerInput,
  SegmentFilters,
  SegmentInput,
} from '@/modules/customers/types'

// Segmentos ficam sob a mesma raiz: a listagem de clientes exibe o segmento e precisa ser
// invalidada junto quando um segmento muda.
export const customersKeys = {
  all: ['customers'] as const,
  list: (filters: CustomerFilters) => [...customersKeys.all, 'list', filters] as const,
  detail: (id: string) => [...customersKeys.all, 'detail', id] as const,
  addresses: (id: string) => [...customersKeys.detail(id), 'addresses'] as const,
  contacts: (id: string) => [...customersKeys.detail(id), 'contacts'] as const,
  segments: (filters: SegmentFilters) => [...customersKeys.all, 'segments', filters] as const,
  segmentOptions: () => [...customersKeys.all, 'segments', 'options'] as const,
}

export function useCustomersList(filters: MaybeRefOrGetter<CustomerFilters>) {
  return useQuery({
    queryKey: computed(() => customersKeys.list(toValue(filters))),
    queryFn: () => api.listCustomers(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useCustomer(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => customersKeys.detail(toValue(id))),
    queryFn: () => api.getCustomer(toValue(id)),
  })
}

export function useAddresses(customerId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => customersKeys.addresses(toValue(customerId))),
    queryFn: () => api.listAddresses(toValue(customerId)),
    enabled: computed(() => Boolean(toValue(customerId))),
  })
}

export function useContacts(customerId: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: computed(() => customersKeys.contacts(toValue(customerId))),
    queryFn: () => api.listContacts(toValue(customerId)),
  })
}

export function useSegmentsList(filters: MaybeRefOrGetter<SegmentFilters>) {
  return useQuery({
    queryKey: computed(() => customersKeys.segments(toValue(filters))),
    queryFn: () => api.listSegments(toValue(filters)),
    placeholderData: keepPreviousData,
  })
}

export function useSegmentOptions(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery({
    queryKey: customersKeys.segmentOptions(),
    queryFn: api.listSegmentOptions,
    enabled: computed(() => toValue(enabled)),
  })
}

/**
 * Mutation que invalida tudo sob `customers` ao terminar — inclusive no erro: um 409/422
 * (segmento inativado por outra pessoa, papel movido) significa que a tela está desatualizada.
 */
function useCustomersMutation<Input, Output>(mutationFn: (input: Input) => Promise<Output>) {
  const queryClient = useQueryClient()
  return useMutation({
    // Wrapper: o TanStack passa um 2º argumento (contexto) que não pertence à API.
    mutationFn: (input: Input) => mutationFn(input),
    onSettled: () => queryClient.invalidateQueries({ queryKey: customersKeys.all }),
  })
}

export const useSaveCustomer = () =>
  useCustomersMutation((input: { id?: string; data: CustomerInput }) =>
    input.id ? api.updateCustomer(input.id, input.data) : api.createCustomer(input.data),
  )

export const useSetCustomerActive = () =>
  useCustomersMutation((input: { id: string; active: boolean }) =>
    api.setCustomerActive(input.id, input.active),
  )

export const useSaveSegment = () =>
  useCustomersMutation((input: { id?: string; data: SegmentInput }) =>
    input.id
      ? api.updateSegment(input.id, { name: input.data.name, description: input.data.description })
      : api.createSegment(input.data),
  )

export const useSetSegmentActive = () =>
  useCustomersMutation((input: { id: string; active: boolean }) =>
    api.setSegmentActive(input.id, input.active),
  )

export const useSaveAddress = (customerId: string) =>
  useCustomersMutation((input: { id?: string; data: AddressInput }) =>
    api.saveAddress(customerId, input.data, input.id),
  )

export const useSetAddressRole = (customerId: string) =>
  useCustomersMutation((input: { id: string; role: AddressRole }) =>
    api.setAddressRole(customerId, input.id, input.role),
  )

export const useRemoveAddress = (customerId: string) =>
  useCustomersMutation((id: string) => api.removeAddress(customerId, id))

export const useSaveContact = (customerId: string) =>
  useCustomersMutation((input: { id?: string; data: ContactInput }) =>
    api.saveContact(customerId, input.data, input.id),
  )

export const useSetPrimaryContact = (customerId: string) =>
  useCustomersMutation((id: string) => api.setPrimaryContact(customerId, id))

export const useRemoveContact = (customerId: string) =>
  useCustomersMutation((id: string) => api.removeContact(customerId, id))
