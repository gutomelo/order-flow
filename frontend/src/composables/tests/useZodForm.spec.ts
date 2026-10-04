import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { z } from 'zod'

import { createAppI18n } from '@/app/providers/i18n'
import { useZodForm } from '@/composables/useZodForm'
import { ApiError } from '@/services/http/apiError'

const schema = z.object({
  sku: z.string().min(1, { error: 'validation.required' }),
  barcode: z.string(),
})

function setup() {
  let form!: ReturnType<typeof useZodForm<typeof schema>>
  mount(
    defineComponent({
      setup() {
        form = useZodForm(schema, { sku: 'A-1', barcode: '' })
        return () => h('div')
      },
    }),
    { global: { plugins: [createAppI18n()] } },
  )
  return form
}

describe('useZodForm', () => {
  it('translates client-side validation messages', async () => {
    const form = setup()
    form.values.sku = ''

    expect(await form.submit(async () => undefined)).toBe(false)
    expect(form.errors.value.sku).toBe('Campo obrigatório.')
  })

  it('shows domain errors tied to a field next to that field', async () => {
    const form = setup()
    const general: unknown[] = []

    await form.submit(
      () =>
        Promise.reject(
          new ApiError({
            status: 422,
            code: 'INVALID_BARCODE',
            message: 'Código de barras inválido.',
            details: { field: 'barcode' },
          }),
        ),
      (error) => general.push(error),
    )

    expect(form.errors.value.barcode).toBe('Código de barras inválido.')
    expect(general).toEqual([])
  })

  it('maps backend VALIDATION_ERROR fields', async () => {
    const form = setup()

    await form.submit(() =>
      Promise.reject(
        new ApiError({
          status: 400,
          code: 'VALIDATION_ERROR',
          message: '',
          details: { fields: { sku: ['SKU muito longo.'] } },
        }),
      ),
    )

    expect(form.errors.value.sku).toBe('SKU muito longo.')
  })

  it('leaves errors without a matching field to the caller', async () => {
    const form = setup()
    const general: unknown[] = []

    await form.submit(
      () =>
        Promise.reject(new ApiError({ status: 409, code: 'CONFLICT', message: 'x', details: {} })),
      (error) => general.push(error),
    )

    expect(general).toHaveLength(1)
  })

  it('prevents double submission while a request is in flight', async () => {
    const form = setup()
    let calls = 0
    const slow = () => new Promise((resolve) => setTimeout(resolve, 10, ++calls))

    await Promise.all([form.submit(slow), form.submit(slow)])

    expect(calls).toBe(1)
  })
})
