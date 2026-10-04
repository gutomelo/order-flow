import axios, { type AxiosInstance } from 'axios'

import { toApiError } from '@/services/http/apiError'

export const REQUEST_ID_HEADER = 'X-Request-ID'

/**
 * Cliente HTTP único da aplicação. Componentes nunca chamam axios diretamente:
 * usam as funções `api/` de cada feature, que usam este cliente.
 *
 * - X-Request-ID por requisição (correlação com os logs do backend);
 * - erros sempre normalizados em `ApiError`.
 *
 * Autenticação (Bearer + refresh) e Idempotency-Key entram na Phase 2 e 6.
 */
export function createHttpClient(baseURL = '/api/v1'): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: 15_000,
    headers: { Accept: 'application/json' },
  })

  client.interceptors.request.use((config) => {
    config.headers.set(REQUEST_ID_HEADER, crypto.randomUUID())
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    (error: unknown) => Promise.reject(toApiError(error)),
  )

  return client
}

export const http = createHttpClient()
