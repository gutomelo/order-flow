import type { Order, Quote } from '@/modules/orders/types'

export function buildQuote(overrides: Partial<Quote> = {}): Quote {
  return {
    lines: [
      {
        product_id: 'p-cola',
        sku: 'COLA',
        product_name: 'Refrigerante Cola',
        quantity: 2,
        unit_price: '3.50',
        line_total: '7.00',
        price_source: 'DEFAULT',
      },
    ],
    subtotal: '7.00',
    discount_total: '0.00',
    shipping_total: '0.00',
    total: '7.00',
    currency: 'BRL',
    ...overrides,
  }
}

export function buildOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: 'o-1',
    number: null,
    status: 'DRAFT',
    customer: {
      id: 'c-1',
      display_name: 'Mercado Central',
      legal_name: 'Mercado Central Ltda',
      tax_id_formatted: '11.222.333/0001-81',
    },
    purchase_order_number: '',
    total: '7.00',
    currency: 'BRL',
    lines_count: 1,
    submitted_at: null,
    payment_due_at: null,
    created_at: '2026-10-05T12:00:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    warehouse: { id: 'w-1', code: 'CD-SP', name: 'CD São Paulo' },
    shipping_address_id: 'a-1',
    shipping: {
      address_id: 'a-1',
      label: 'Matriz',
      postal_code: '01310100',
      street: 'Avenida Paulista',
      number: '1000',
      complement: '',
      district: 'Bela Vista',
      city: 'São Paulo',
      state: 'SP',
    },
    notes: '',
    subtotal: '7.00',
    discount_total: '0.00',
    shipping_total: '0.00',
    created_by: { id: 'u-1', name: 'Ana' },
    lines: [
      {
        id: 'l-1',
        product_id: 'p-cola',
        sku: 'COLA',
        product_name: 'Refrigerante Cola',
        quantity: 2,
        unit_price: '3.50',
        discount_amount: '0.00',
        line_total: '7.00',
        price_source: 'DEFAULT',
      },
    ],
    payments: [],
    shipment: null,
    history: [
      {
        id: 'h-1',
        from_status: null,
        to_status: 'DRAFT',
        changed_by: { id: 'u-1', name: 'Ana' },
        changed_at: '2026-10-05T12:00:00Z',
        reason: '',
      },
    ],
    ...overrides,
  }
}
