import { isAxiosError } from 'axios'

/** Códigos gerados no cliente quando não há envelope de erro do backend. */
export type ClientErrorCode = 'NETWORK_ERROR' | 'UNEXPECTED_RESPONSE' | 'UNKNOWN_ERROR'

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
  }
}

/** Erro normalizado de qualquer chamada HTTP — o único tipo de erro que a UI precisa tratar. */
export class ApiError extends Error {
  readonly status: number | null
  readonly code: string
  readonly details: Record<string, unknown>
  readonly requestId: string | null

  constructor(params: {
    status: number | null
    code: string
    message: string
    details?: Record<string, unknown>
    requestId?: string | null
  }) {
    super(params.message)
    this.name = 'ApiError'
    this.status = params.status
    this.code = params.code
    this.details = params.details ?? {}
    this.requestId = params.requestId ?? null
  }
}

export function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== 'object' || value === null || !('error' in value)) {
    return false
  }
  const error = (value as { error: unknown }).error
  return (
    typeof error === 'object' &&
    error !== null &&
    typeof (error as { code?: unknown }).code === 'string' &&
    typeof (error as { message?: unknown }).message === 'string'
  )
}

function readRequestId(headers: unknown): string | null {
  if (typeof headers !== 'object' || headers === null) {
    return null
  }
  const value = (headers as Record<string, unknown>)['x-request-id']
  return typeof value === 'string' ? value : null
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error
  }

  if (isAxiosError(error)) {
    const response = error.response
    const requestId =
      readRequestId(response?.headers) ?? readRequestId(error.config?.headers) ?? null

    if (!response) {
      return new ApiError({
        status: null,
        code: 'NETWORK_ERROR',
        message: error.message,
        requestId,
      })
    }

    if (isApiErrorEnvelope(response.data)) {
      const { code, message, details } = response.data.error
      return new ApiError({ status: response.status, code, message, details, requestId })
    }

    return new ApiError({
      status: response.status,
      code: 'UNEXPECTED_RESPONSE',
      message: error.message,
      requestId,
    })
  }

  return new ApiError({
    status: null,
    code: 'UNKNOWN_ERROR',
    message: error instanceof Error ? error.message : String(error),
  })
}
