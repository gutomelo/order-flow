import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { AxiosError } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/services/http/apiError'
import { configureAuth, createHttpClient } from '@/services/http/client'

type Handler = (config: InternalAxiosRequestConfig) => { status: number; data?: unknown }

/** Adapter em memória: simula o servidor sem rede e sem bibliotecas extras. */
function fakeServer(handler: Handler): AxiosAdapter {
  return async (config) => {
    const { status, data } = handler(config)
    const response = { status, data, headers: {}, config, statusText: '' } as AxiosResponse
    if (status >= 400) {
      throw new AxiosError('error', String(status), config, undefined, response)
    }
    return response
  }
}

function clientWith(handler: Handler) {
  const client = createHttpClient()
  client.defaults.adapter = fakeServer(handler)
  return client
}

afterEach(() => configureAuth(null))

describe('http client', () => {
  it('sends the access token, request id and anti-CSRF header', async () => {
    configureAuth({
      getAccessToken: () => 'token-1',
      refreshAccessToken: vi.fn(),
      onSessionExpired: vi.fn(),
    })
    let seen: InternalAxiosRequestConfig | undefined
    const client = clientWith((config) => {
      seen = config
      return { status: 200, data: {} }
    })

    await client.get('/orders')

    expect(seen?.headers.get('Authorization')).toBe('Bearer token-1')
    expect(seen?.headers.get('X-Requested-With')).toBe('XMLHttpRequest')
    expect(seen?.headers.get('X-Request-ID')).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('refreshes once on 401 and retries the original request with the new token', async () => {
    let token = 'expired'
    const refreshAccessToken = vi.fn(async () => (token = 'fresh'))
    configureAuth({ getAccessToken: () => token, refreshAccessToken, onSessionExpired: vi.fn() })
    const client = clientWith((config) =>
      config.headers.get('Authorization') === 'Bearer fresh'
        ? { status: 200, data: { ok: true } }
        : { status: 401, data: { error: { code: 'NOT_AUTHENTICATED', message: '', details: {} } } },
    )

    const response = await client.get('/orders')

    expect(response.data).toEqual({ ok: true })
    expect(refreshAccessToken).toHaveBeenCalledTimes(1)
  })

  it('expires the session when the refresh fails', async () => {
    const onSessionExpired = vi.fn()
    configureAuth({
      getAccessToken: () => 'expired',
      refreshAccessToken: async () => null,
      onSessionExpired,
    })
    const client = clientWith(() => ({ status: 401 }))

    await expect(client.get('/orders')).rejects.toBeInstanceOf(ApiError)
    expect(onSessionExpired).toHaveBeenCalledTimes(1)
  })

  it('never refreshes for session endpoints (avoids loops)', async () => {
    const refreshAccessToken = vi.fn()
    configureAuth({ getAccessToken: () => null, refreshAccessToken, onSessionExpired: vi.fn() })
    const client = clientWith(() => ({ status: 401 }))

    await expect(client.post('/auth/login', {})).rejects.toBeInstanceOf(ApiError)
    expect(refreshAccessToken).not.toHaveBeenCalled()
  })
})
