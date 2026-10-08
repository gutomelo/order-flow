import { describe, expect, it } from 'vitest'

import { localDayBoundsToUtc } from '@/utils/datetime'

describe('localDayBoundsToUtc', () => {
  it('covers the whole local day, from local midnight to the next one', () => {
    const { start, end } = localDayBoundsToUtc('2026-10-04')

    const startDate = new Date(start)
    const endDate = new Date(end)
    expect([startDate.getFullYear(), startDate.getMonth(), startDate.getDate()]).toEqual([
      2026, 9, 4,
    ])
    expect([startDate.getHours(), startDate.getMinutes()]).toEqual([0, 0])
    expect(endDate.getDate()).toBe(5)
    expect(endDate.getHours()).toBe(0)
  })

  it('returns UTC ISO strings for the API', () => {
    const { start } = localDayBoundsToUtc('2026-10-04')

    expect(start).toMatch(/Z$/)
  })
})
