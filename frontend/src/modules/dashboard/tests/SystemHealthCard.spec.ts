import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchReadiness } from '@/modules/dashboard/api/healthApi'
import SystemHealthCard from '@/modules/dashboard/components/SystemHealthCard.vue'
import { ApiError } from '@/services/http/apiError'
import { mountWithPlugins } from '@/testing/mountWithPlugins'

vi.mock('@/modules/dashboard/api/healthApi', () => ({ fetchReadiness: vi.fn() }))

const fetchReadinessMock = vi.mocked(fetchReadiness)

describe('SystemHealthCard', () => {
  beforeEach(() => {
    fetchReadinessMock.mockReset()
  })

  it('shows a loading state while checking', async () => {
    fetchReadinessMock.mockReturnValue(new Promise(() => {}))

    const { wrapper } = await mountWithPlugins(SystemHealthCard)

    expect(wrapper.find('[role="status"]').text()).toContain('Verificando serviços')
  })

  it('lists every dependency as operational when healthy', async () => {
    fetchReadinessMock.mockResolvedValue({
      status: 'ok',
      checks: { database: 'ok', cache: 'ok', broker: 'ok' },
    })

    const { wrapper } = await mountWithPlugins(SystemHealthCard)
    await flushPromises()

    expect(wrapper.text()).toContain('Todos os serviços operacionais')
    expect(wrapper.findAll('li')).toHaveLength(3)
    expect(wrapper.text()).toContain('Banco de dados')
  })

  it('identifies the unavailable dependency with text, not only color', async () => {
    fetchReadinessMock.mockResolvedValue({
      status: 'unavailable',
      checks: { database: 'ok', cache: 'ok', broker: 'unavailable' },
    })

    const { wrapper } = await mountWithPlugins(SystemHealthCard)
    await flushPromises()

    expect(wrapper.text()).toContain('Há serviços indisponíveis')
    const broker = wrapper.findAll('li').find((item) => item.text().includes('Fila de mensagens'))
    expect(broker?.text()).toContain('Indisponível')
  })

  it('explains connection failures and shows the support code', async () => {
    fetchReadinessMock.mockRejectedValue(
      new ApiError({ status: null, code: 'NETWORK_ERROR', message: '', requestId: 'req-42' }),
    )

    const { wrapper } = await mountWithPlugins(SystemHealthCard)
    await flushPromises()

    const alert = wrapper.find('[role="alert"]')
    expect(alert.text()).toContain('Não foi possível conectar ao servidor')
    expect(alert.text()).toContain('req-42')
  })
})
