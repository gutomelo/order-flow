import { describe, expect, it } from 'vitest'

import { formatMoney, parseMoneyInput, toMoneyInput } from '@/utils/money'

describe('money', () => {
  it('formats decimal strings as BRL', () => {
    expect(formatMoney('1234.5').replace(/\s/g, ' ')).toBe('R$ 1.234,50')
    expect(formatMoney(null)).toBe('—')
  })

  it.each([
    ['3,5', '3.50'],
    ['1.234,56', '1234.56'],
    ['1234.5', '1234.50'],
    ['R$ 10', '10.00'],
    ['007', '7.00'],
  ])('reads %s as %s', (raw, expected) => {
    expect(parseMoneyInput(raw)).toBe(expected)
  })

  it.each(['', 'abc', '-1', '1,234', '1.2.3'])('rejects %s', (raw) => {
    expect(parseMoneyInput(raw)).toBeNull()
  })

  it('prepares values for pt-BR inputs', () => {
    expect(toMoneyInput('3.50')).toBe('3,50')
  })
})
