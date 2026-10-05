import { describe, expect, it } from 'vitest'

import { useIdempotencyKey } from '@/composables/useIdempotencyKey'

describe('useIdempotencyKey', () => {
  it('keeps the key while the payload is the same and renews it when it changes', () => {
    let payload = { lines: [{ product_id: 'p-1', quantity: 2 }] }
    const keyFor = useIdempotencyKey(() => payload)

    const first = keyFor()
    expect(keyFor()).toBe(first)

    payload = { lines: [{ product_id: 'p-1', quantity: 3 }] }
    expect(keyFor()).not.toBe(first)
  })
})
