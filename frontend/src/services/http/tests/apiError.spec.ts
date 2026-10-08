import { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { describe, expect, it } from 'vitest'

import { ApiError, toApiError } from '@/services/http/apiError'

function axiosErrorWithResponse(status: number, data: unknown, requestId?: string) {
  const config = { headers: new AxiosHeaders() } as InternalAxiosRequestConfig
  const headers = requestId ? { 'x-request-id': requestId } : {}
  return new AxiosError('Request failed', 'ERR_BAD_RESPONSE', config, undefined, {
    status,
    statusText: '',
    headers,
    config,
    data,
  })
}

describe('toApiError', () => {
  it('maps the backend error envelope', () => {
    const error = toApiError(
      axiosErrorWithResponse(
        409,
        {
          error: {
            code: 'INSUFFICIENT_STOCK',
            message: 'Estoque insuficiente.',
            details: { product_id: 'p-1' },
          },
        },
        'req-123',
      ),
    )

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.code).toBe('INSUFFICIENT_STOCK')
    expect(error.message).toBe('Estoque insuficiente.')
    expect(error.details).toEqual({ product_id: 'p-1' })
    expect(error.requestId).toBe('req-123')
  })

  it('flags responses without the envelope as unexpected', () => {
    const error = toApiError(axiosErrorWithResponse(502, '<html>Bad Gateway</html>'))

    expect(error.code).toBe('UNEXPECTED_RESPONSE')
    expect(error.status).toBe(502)
  })

  it('flags requests without response as network errors', () => {
    const error = toApiError(new AxiosError('Network Error', 'ERR_NETWORK'))

    expect(error.code).toBe('NETWORK_ERROR')
    expect(error.status).toBeNull()
  })

  it('wraps non-HTTP errors as unknown', () => {
    const error = toApiError(new TypeError('boom'))

    expect(error.code).toBe('UNKNOWN_ERROR')
  })

  it('returns ApiError instances unchanged', () => {
    const original = new ApiError({ status: 404, code: 'NOT_FOUND', message: 'x' })

    expect(toApiError(original)).toBe(original)
  })
})
