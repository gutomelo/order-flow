import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import App from '@/App.vue'
import * as customersApi from '@/modules/customers/api/customersApi'
import { buildAddress } from '@/modules/customers/tests/fixtures'
import * as inventoryApi from '@/modules/inventory/api/inventoryApi'
import * as ordersApi from '@/modules/orders/api/ordersApi'
import { buildOrder, buildQuote } from '@/modules/orders/tests/fixtures'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

// Os comboboxes (Reka UI) viram botões que escolhem uma opção fixa: aqui testamos o fluxo.
function pickerStub(className: string, option: Record<string, string>) {
  return defineComponent({
    props: { modelValue: { type: Object, default: null }, error: { type: String, default: '' } },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
      return () =>
        h('div', [
          h(
            'button',
            { type: 'button', class: className, onClick: () => emit('update:modelValue', option) },
            props.modelValue ? 'chosen' : 'choose',
          ),
          props.error ? h('p', { class: `${className}-error` }, props.error) : null,
        ])
    },
  })
}

vi.mock('@/modules/orders/components/CustomerPicker.vue', () => ({
  default: pickerStub('pick-customer', {
    id: 'c-1',
    display_name: 'Mercado Central',
    tax_id_formatted: '11.222.333/0001-81',
  }),
}))
vi.mock('@/modules/catalog/components/ProductPicker.vue', () => ({
  default: pickerStub('pick-product', { id: 'p-cola', sku: 'COLA', name: 'Refrigerante Cola' }),
}))
vi.mock('@/modules/orders/api/ordersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof ordersApi>()),
  quoteOrder: vi.fn(),
  placeOrder: vi.fn(),
  createDraft: vi.fn(),
  getOrder: vi.fn(),
}))
vi.mock('@/modules/customers/api/customersApi', async (importOriginal) => ({
  ...(await importOriginal<typeof customersApi>()),
  listAddresses: vi.fn(),
}))
vi.mock('@/modules/inventory/api/inventoryApi', async (importOriginal) => ({
  ...(await importOriginal<typeof inventoryApi>()),
  listWarehouses: vi.fn(),
}))

const orders = vi.mocked(ordersApi)
const seller = buildCurrentUser({
  role: 'SALES',
  permissions: ['orders:read', 'orders:create', 'customers:read', 'inventory:read'],
})

const waitForQuote = () => new Promise((resolve) => setTimeout(resolve, 350))

async function fillNewOrder() {
  const mounted = await mountWithPlugins(App, { route: '/orders/new', user: seller })
  await flushPromises()
  const { wrapper } = mounted
  await wrapper.find('.pick-customer').trigger('click')
  await wrapper.find('.pick-product').trigger('click')
  await wrapper.find('input[inputmode="numeric"]').setValue('2')
  await flushPromises()
  await waitForQuote()
  await flushPromises()
  return mounted
}

describe('OrderEditorPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(inventoryApi.listWarehouses).mockResolvedValue([
      {
        id: 'w-1',
        code: 'CD-SP',
        name: 'CD São Paulo',
        is_active: true,
        created_at: '',
        updated_at: '',
      },
    ])
    vi.mocked(customersApi.listAddresses).mockResolvedValue([buildAddress()])
    orders.quoteOrder.mockResolvedValue(buildQuote())
    orders.getOrder.mockResolvedValue(buildOrder({ status: 'PENDING', number: 1 }))
  })

  it('preselects the default address and the only warehouse and shows the backend quote', async () => {
    const { wrapper } = await fillNewOrder()

    const selects = wrapper.findAll('select')
    expect(selects.map((s) => (s.element as HTMLSelectElement).value)).toEqual(['a-1', 'w-1'])
    expect(orders.quoteOrder).toHaveBeenLastCalledWith({
      customer_id: 'c-1',
      lines: [{ product_id: 'p-cola', quantity: 2 }],
    })
    expect(wrapper.find('aside[aria-labelledby="order-summary-heading"]').text()).toMatch(
      /Total estimado\s*R\$\s*7,00/,
    )
  })

  it('submits with an idempotency key and the total the seller saw', async () => {
    orders.placeOrder.mockResolvedValue(buildOrder({ id: 'o-9', status: 'PENDING', number: 1 }))
    const { wrapper, router } = await fillNewOrder()

    await wrapper.find('#order-editor').trigger('submit')
    await flushPromises()
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/orders/o-9'))

    const [data, key] = orders.placeOrder.mock.calls[0] ?? []
    expect(data).toEqual({
      customer_id: 'c-1',
      warehouse_id: 'w-1',
      shipping_address_id: 'a-1',
      purchase_order_number: '',
      notes: '',
      lines: [{ product_id: 'p-cola', quantity: 2 }],
      expected_total: '7.00',
    })
    expect(key).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('reuses the same key when the same order is sent again after a failure', async () => {
    orders.placeOrder.mockRejectedValueOnce(
      new ApiError({ status: null, code: 'NETWORK_ERROR', message: 'Sem conexão.' }),
    )
    orders.placeOrder.mockResolvedValueOnce(buildOrder({ id: 'o-9', status: 'PENDING', number: 1 }))
    const { wrapper } = await fillNewOrder()

    await wrapper.find('#order-editor').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Sem conexão.')
    await wrapper.find('#order-editor').trigger('submit')
    await flushPromises()

    const keys = orders.placeOrder.mock.calls.map((call) => call[1])
    expect(keys).toHaveLength(2)
    expect(keys[0]).toBe(keys[1])
  })

  it('explains a price change instead of submitting a total nobody saw', async () => {
    orders.placeOrder.mockRejectedValue(
      new ApiError({
        status: 409,
        code: 'PRICES_CHANGED',
        message: 'Os preços mudaram.',
        details: { expected: '7.00', actual: '8.00' },
      }),
    )
    const { wrapper } = await fillNewOrder()

    await wrapper.find('#order-editor').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toMatch(/novo total é R\$\s*8,00/)
    expect(orders.quoteOrder.mock.calls.length).toBeGreaterThan(1) // prévia recarregada
  })

  it('marks the line whose product has no price for this customer', async () => {
    orders.quoteOrder.mockRejectedValue(
      new ApiError({
        status: 422,
        code: 'PRICE_NOT_FOUND',
        message: 'Há produtos sem preço para este cliente.',
        details: { product_ids: ['p-cola'] },
      }),
    )
    const { wrapper } = await fillNewOrder()

    expect(wrapper.find('.pick-product-error').text()).toBe(
      'Há produtos sem preço para este cliente.',
    )
    expect(wrapper.find('aside[aria-labelledby="order-summary-heading"]').text()).toContain(
      'Há itens sem preço',
    )
  })

  it('requires a customer before saving and focuses it', async () => {
    const { wrapper } = await mountWithPlugins(App, { route: '/orders/new', user: seller })
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Salvar rascunho')
      ?.trigger('click')
    await flushPromises()

    expect(wrapper.find('.pick-customer-error').text()).toBe('Campo obrigatório.')
    expect(orders.createDraft).not.toHaveBeenCalled()
  })
})
