import { QueryClient } from '@tanstack/vue-query'

import { ApiError } from '@/services/http/apiError'

const MAX_RETRIES = 2

/** Erros 4xx são definitivos (validação, permissão, conflito): repetir não muda o resultado. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status !== null && error.status < 500) {
    return false
  }
  return failureCount < MAX_RETRIES
}

export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: shouldRetry,
        refetchOnWindowFocus: true,
      },
      mutations: {
        // Mutations nunca são repetidas automaticamente: retries seguros dependem de
        // Idempotency-Key (ADR-012), decidido caso a caso.
        retry: false,
      },
    },
  })
}
