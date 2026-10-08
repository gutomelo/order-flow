import axios, { isAxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import { toApiError } from '@/services/http/apiError'

export const REQUEST_ID_HEADER = 'X-Request-ID'

/**
 * Integração com a sessão, registrada pelo store de sessão no bootstrap da aplicação.
 * O cliente não importa o store (evita dependência circular e facilita testes).
 */
export interface AuthHooks {
  getAccessToken(): string | null
  /** Renova a sessão (cookie HttpOnly) e retorna o novo access token, ou null se expirou. */
  refreshAccessToken(): Promise<string | null>
  onSessionExpired(): void
}

let authHooks: AuthHooks | null = null

export function configureAuth(hooks: AuthHooks | null): void {
  authHooks = hooks
}

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retriedAfterRefresh?: boolean
}

// Endpoints de sessão nunca disparam refresh automático (evita laço infinito).
function isSessionEndpoint(url: string | undefined): boolean {
  return url?.startsWith('/auth/') ?? false
}

/**
 * Cliente HTTP único da aplicação. Componentes nunca chamam axios diretamente:
 * usam as funções `api/` de cada feature, que usam este cliente.
 *
 * - `X-Request-ID` por requisição (correlação com os logs do backend);
 * - `X-Requested-With` (exigido pelos endpoints de sessão — defesa contra CSRF, ADR-007);
 * - `Authorization: Bearer` a partir da sessão em memória;
 * - 401 → um refresh e uma nova tentativa;
 * - erros sempre normalizados em `ApiError`.
 */
export function createHttpClient(baseURL = '/api/v1'): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: 15_000,
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
  })

  client.interceptors.request.use((config) => {
    config.headers.set(REQUEST_ID_HEADER, crypto.randomUUID())
    const token = authHooks?.getAccessToken()
    if (token) {
      config.headers.set('Authorization', `Bearer ${token}`)
    }
    return config
  })

  client.interceptors.response.use(
    (response) => response,
    async (error: unknown) => {
      if (isAxiosError(error) && error.response?.status === 401 && authHooks) {
        const config = error.config as RetriableConfig | undefined
        if (config && !config._retriedAfterRefresh && !isSessionEndpoint(config.url)) {
          config._retriedAfterRefresh = true
          const token = await authHooks.refreshAccessToken()
          if (token) {
            return client.request(config)
          }
          authHooks.onSessionExpired()
        }
      }
      return Promise.reject(toApiError(error))
    },
  )

  return client
}

export const http = createHttpClient()
