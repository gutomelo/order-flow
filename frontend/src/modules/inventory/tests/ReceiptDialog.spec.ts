/* eslint-disable vue/one-component-per-file -- stub do combobox e host do diálogo no teste */
import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import * as inventoryApi from '@/modules/inventory/api/inventoryApi'
import ReceiptDialog from '@/modules/inventory/components/ReceiptDialog.vue'
import { ApiError } from '@/services/http/apiError'
import { buildCurrentUser, mountWithPlugins } from '@/testing/mountWithPlugins'

// O combobox (Reka UI) é substituído por um stub: aqui testamos as regras do formulário.
vi.mock('@/modules/catalog/components/ProductPicker.vue', () => ({
  default: defineComponent({
    props: { modelValue: { type: Object, default: null }, error: { type: String, default: '' } },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
      return () =>
        h('div', { class: 'picker' }, [
          h(
            'button',
            {
              type: 'button',
              class: 'pick',
              onClick: () => emit('update:modelValue', { id: 'p-cafe', sku: 'CAFE', name: 'Café' }),
            },
            props.modelValue ? 'chosen' : 'choose',
          ),
          props.error ? h('p', { class: 'picker-error' }, props.error) : null,
        ])
    },
  }),
}))

vi.mock('@/modules/inventory/api/inventoryApi', async (importOriginal) => ({
  ...(await importOriginal<typeof inventoryApi>()),
  listWarehouses: vi.fn(),
  receiveStock: vi.fn(),
}))

const api = vi.mocked(inventoryApi)
const operator = buildCurrentUser({ role: 'WAREHOUSE', permissions: ['inventory:update'] })

async function mountDialog() {
  const Host = defineComponent({ setup: () => () => h(ReceiptDialog, { open: ref(true).value }) })
  const mounted = await mountWithPlugins(Host, { user: operator })
  await flushPromises()
  return mounted.wrapper
}

describe('ReceiptDialog', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listWarehouses.mockResolvedValue([
      {
        id: 'w-1',
        code: 'CD-SP',
        name: 'CD São Paulo',
        is_active: true,
        created_at: '',
        updated_at: '',
      },
      { id: 'w-2', code: 'OLD', name: 'Antigo', is_active: false, created_at: '', updated_at: '' },
    ])
  })

  it('offers only active warehouses', async () => {
    const wrapper = await mountDialog()

    const options = wrapper.findAll('select option').map((option) => option.text())
    expect(options).toContain('CD-SP — CD São Paulo')
    expect(options.join()).not.toContain('Antigo')
  })

  it('validates every line before calling the API', async () => {
    const wrapper = await mountDialog()

    await wrapper.find('select').setValue('w-1')
    await wrapper.find('#receipt-form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.picker-error').text()).toBe('Campo obrigatório.')
    expect(wrapper.text()).toContain('Informe um número inteiro.')
    expect(api.receiveStock).not.toHaveBeenCalled()
  })

  it('sends warehouse, document and parsed lines', async () => {
    api.receiveStock.mockResolvedValue({})
    const wrapper = await mountDialog()

    await wrapper.find('select').setValue('w-1')
    await wrapper.find('.pick').trigger('click')
    const inputs = wrapper.findAll('input')
    await inputs.find((i) => i.attributes('inputmode') === 'numeric')?.setValue('12')
    await inputs[0]?.setValue('NF-1001')
    await wrapper.find('#receipt-form').trigger('submit')
    await flushPromises()

    expect(api.receiveStock).toHaveBeenCalledWith({
      warehouse_id: 'w-1',
      supplier_id: null,
      document_number: 'NF-1001',
      notes: '',
      lines: [{ product_id: 'p-cafe', quantity: 12 }],
    })
  })

  it('marks the line whose product was rejected by the backend', async () => {
    api.receiveStock.mockRejectedValue(
      new ApiError({
        status: 422,
        code: 'PRODUCT_NOT_AVAILABLE',
        message: 'Produto não encontrado ou inativo.',
        details: { product_ids: ['p-cafe'] },
      }),
    )
    const wrapper = await mountDialog()

    await wrapper.find('select').setValue('w-1')
    await wrapper.find('.pick').trigger('click')
    await wrapper
      .findAll('input')
      .find((i) => i.attributes('inputmode') === 'numeric')
      ?.setValue('1')
    await wrapper.find('#receipt-form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.picker-error').text()).toBe('Produto não encontrado ou inativo.')
  })

  it('shows a duplicated invoice next to the document field', async () => {
    api.receiveStock.mockRejectedValue(
      new ApiError({
        status: 409,
        code: 'RECEIPT_ALREADY_REGISTERED',
        message: 'Este documento já foi recebido para este fornecedor.',
        details: { field: 'document_number' },
      }),
    )
    const wrapper = await mountDialog()

    await wrapper.find('select').setValue('w-1')
    await wrapper.find('.pick').trigger('click')
    const inputs = wrapper.findAll('input')
    await inputs.find((i) => i.attributes('inputmode') === 'numeric')?.setValue('1')
    await inputs[0]?.setValue('NF-1')
    await wrapper.find('#receipt-form').trigger('submit')
    await flushPromises()

    expect(inputs[0]?.attributes('aria-invalid')).toBe('true')
    expect(wrapper.text()).toContain('Este documento já foi recebido')
  })
})
