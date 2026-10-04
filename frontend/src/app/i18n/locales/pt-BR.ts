// Chaves em inglês, textos em pt-BR (regra de idioma do projeto).
export default {
  app: {
    name: 'OrderFlow',
  },
  nav: {
    label: 'Navegação principal',
    dashboard: 'Dashboard',
  },
  layout: {
    skipToContent: 'Pular para o conteúdo',
    collapseSidebar: 'Recolher menu lateral',
    expandSidebar: 'Expandir menu lateral',
    openMenu: 'Abrir menu',
    closeMenu: 'Fechar menu',
  },
  theme: {
    label: 'Tema',
    light: 'Claro',
    dark: 'Escuro',
    system: 'Sistema',
  },
  dashboard: {
    title: 'Dashboard',
    description: 'Visão geral do negócio.',
    empty: {
      title: 'Ainda não há indicadores para exibir',
      description:
        'Pedidos, faturamento e alertas de estoque aparecerão aqui assim que os primeiros pedidos forem registrados.',
    },
    health: {
      title: 'Status do sistema',
      description: 'Conectividade da API com os serviços de infraestrutura.',
      checkedAt: 'Verificado às {time}',
      refresh: 'Atualizar',
      loading: 'Verificando serviços…',
      overall: {
        ok: 'Todos os serviços operacionais',
        unavailable: 'Há serviços indisponíveis',
      },
      status: {
        ok: 'Operacional',
        unavailable: 'Indisponível',
      },
      checks: {
        database: 'Banco de dados',
        cache: 'Cache',
        broker: 'Fila de mensagens',
      },
    },
  },
  notFound: {
    title: 'Página não encontrada',
    description: 'O endereço acessado não existe ou foi movido.',
    backToDashboard: 'Voltar para o dashboard',
  },
  errors: {
    NETWORK_ERROR: 'Não foi possível conectar ao servidor. Verifique sua conexão.',
    UNEXPECTED_RESPONSE: 'O servidor retornou uma resposta inesperada.',
    UNKNOWN_ERROR: 'Ocorreu um erro inesperado.',
    requestId: 'Código para suporte: {requestId}',
  },
}
