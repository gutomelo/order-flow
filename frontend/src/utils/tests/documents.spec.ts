import { describe, expect, it } from 'vitest'

import { isValidCnpj, normalizeCnpj } from '@/utils/documents'

describe('CNPJ', () => {
  it.each(['11.222.333/0001-81', '11222333000181', '12.ABC.345/01DE-35', '12abc34501de35'])(
    'accepts %s',
    (value) => {
      expect(isValidCnpj(value)).toBe(true)
    },
  )

  it.each(['11.222.333/0001-82', '12.ABC.345/01DE-36', '11111111111111', '12ABC34501DEAB', ''])(
    'rejects %s',
    (value) => {
      expect(isValidCnpj(value)).toBe(false)
    },
  )

  it('normalizes masks and case', () => {
    expect(normalizeCnpj(' 12.abc.345/01de-35 ')).toBe('12ABC34501DE35')
  })
})
