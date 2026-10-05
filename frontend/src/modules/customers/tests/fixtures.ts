import type { Customer, CustomerAddress, CustomerContact, Segment } from '@/modules/customers/types'

export function buildSegment(overrides: Partial<Segment> = {}): Segment {
  return {
    id: 'seg-1',
    code: 'ATACADO',
    name: 'Atacado',
    description: '',
    active_customers: 1,
    is_active: true,
    created_at: '2026-10-05T12:00:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    ...overrides,
  }
}

export function buildCustomer(overrides: Partial<Customer> = {}): Customer {
  return {
    id: 'c-1',
    legal_name: 'Mercado Central Ltda',
    trade_name: 'Mercado Central',
    display_name: 'Mercado Central',
    tax_id: '11222333000181',
    tax_id_formatted: '11.222.333/0001-81',
    email: 'compras@mercado.com',
    phone: '',
    segment: { id: 'seg-1', code: 'ATACADO', name: 'Atacado', is_active: true },
    is_active: true,
    created_at: '2026-10-05T12:00:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    ...overrides,
  }
}

export function buildAddress(overrides: Partial<CustomerAddress> = {}): CustomerAddress {
  return {
    id: 'a-1',
    label: 'Matriz',
    postal_code: '01310100',
    street: 'Avenida Paulista',
    number: '1000',
    complement: '',
    district: 'Bela Vista',
    city: 'São Paulo',
    state: 'SP',
    is_billing: true,
    is_default_shipping: true,
    created_at: '2026-10-05T12:00:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    ...overrides,
  }
}

export function buildContact(overrides: Partial<CustomerContact> = {}): CustomerContact {
  return {
    id: 'ct-1',
    name: 'Ana Lima',
    job_title: 'Compras',
    email: 'ana@mercado.com',
    phone: '',
    is_primary: true,
    created_at: '2026-10-05T12:00:00Z',
    updated_at: '2026-10-05T12:00:00Z',
    ...overrides,
  }
}

export const page = <T>(results: T[]) => ({
  count: results.length,
  next: null,
  previous: null,
  results,
})
