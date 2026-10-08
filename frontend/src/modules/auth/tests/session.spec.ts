import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '@/modules/auth/api/authApi'
import { useSessionStore } from '@/modules/auth/stores/session'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser } from '@/testing/mountWithPlugins'

vi.mock('@/modules/auth/api/authApi')

const api = vi.mocked(authApi)

describe('session store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('keeps the access token and user in memory after login', async () => {
    api.login.mockResolvedValue({ access: 'access-1', user: buildCurrentUser() })
    const session = useSessionStore()

    await session.login('ana@acme.com', 'secret')

    expect(session.isAuthenticated).toBe(true)
    expect(session.accessToken).toBe('access-1')
    expect(window.localStorage.length).toBe(0) // nunca persistido
  })

  it('checks permissions from the current user', async () => {
    api.login.mockResolvedValue({
      access: 'a',
      user: buildCurrentUser({ permissions: ['orders:read'] }),
    })
    const session = useSessionStore()
    await session.login('ana@acme.com', 'secret')

    expect(session.can('orders:read')).toBe(true)
    expect(session.can('users:manage')).toBe(false)
    expect(session.can(undefined)).toBe(true)
  })

  it('shares a single refresh between concurrent callers', async () => {
    let resolve!: (token: string) => void
    api.refreshSession.mockReturnValue(new Promise((r) => (resolve = r)))
    const session = useSessionStore()

    const first = session.refresh()
    const second = session.refresh()
    resolve('access-2')

    expect(await first).toBe('access-2')
    expect(await second).toBe('access-2')
    expect(api.refreshSession).toHaveBeenCalledTimes(1)
  })

  it('clears the session when refresh fails', async () => {
    api.refreshSession.mockRejectedValue(
      new ApiError({ status: 401, code: 'INVALID_REFRESH_TOKEN', message: '' }),
    )
    const session = useSessionStore()
    session.accessToken = 'stale'

    expect(await session.refresh()).toBeNull()
    expect(session.accessToken).toBeNull()
  })

  it('restores the session from the refresh cookie only once', async () => {
    api.refreshSession.mockResolvedValue('access-3')
    api.fetchCurrentUser.mockResolvedValue(buildCurrentUser())
    const session = useSessionStore()

    await session.restore()
    await session.restore()

    expect(session.isAuthenticated).toBe(true)
    expect(api.refreshSession).toHaveBeenCalledTimes(1)
  })

  it('clears the local session even if the logout request fails', async () => {
    api.logout.mockRejectedValue(new ApiError({ status: null, code: 'NETWORK_ERROR', message: '' }))
    const session = useSessionStore()
    session.accessToken = 'a'
    session.user = buildCurrentUser()

    await expect(session.logout()).rejects.toBeInstanceOf(ApiError)
    expect(session.isAuthenticated).toBe(false)
  })
})
