import { describe, expect, it } from 'vitest'

import { shouldRetry } from '@/app/providers/queryClient'
import { ApiError } from '@/services/http/apiError'

const apiError = (status: number | null) => new ApiError({ status, code: 'X', message: 'x' })

describe('shouldRetry', () => {
  it('never retries client errors (4xx)', () => {
    expect(shouldRetry(0, apiError(404))).toBe(false)
    expect(shouldRetry(0, apiError(409))).toBe(false)
  })

  it('retries server and network errors up to the limit', () => {
    expect(shouldRetry(0, apiError(503))).toBe(true)
    expect(shouldRetry(1, apiError(null))).toBe(true)
    expect(shouldRetry(2, apiError(503))).toBe(false)
  })
})
