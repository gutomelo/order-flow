// Chaves em inglês, textos em pt-BR (regra de idioma do projeto).
export default {
  app: {
    name: 'OrderFlow',
  },
  common: {
    cancel: 'Cancelar',
    save: 'Salvar',
    close: 'Fechar',
    retry: 'Tentar novamente',
    loading: 'Carregando…',
    actions: 'Ações',
  },
  validation: {
    required: 'Campo obrigatório.',
    email: 'Informe um e-mail válido.',
    passwordMin: 'A senha deve ter pelo menos 8 caracteres.',
  },
  roles: {
    ADMIN: 'Administrador',
    MANAGER: 'Gestor',
    SALES: 'Vendas',
    WAREHOUSE: 'Depósito',
    FINANCE: 'Financeiro',
    VIEWER: 'Leitura',
  },
  nav: {
    label: 'Navegação principal',
    dashboard: 'Dashboard',
    users: 'Usuários',
    teams: 'Equipes',
  },
  auth: {
    login: {
      title: 'Entrar',
      description: 'Acesse com o e-mail e a senha da sua organização.',
      email: 'E-mail',
      password: 'Senha',
      submit: 'Entrar',
    },
  },
  userMenu: {
    label: 'Menu do usuário',
    logout: 'Sair',
  },
  pagination: {
    label: 'Paginação',
    range: '{first}–{last} de {count}',
    page: 'Página {page} de {total}',
    previous: 'Página anterior',
    next: 'Próxima página',
  },
  users: {
    title: 'Usuários',
    description: 'Pessoas da sua organização, seus papéis e equipes.',
    you: 'você',
    neverLoggedIn: 'Nunca acessou',
    fields: {
      name: 'Nome',
      firstName: 'Nome',
      lastName: 'Sobrenome',
      email: 'E-mail',
      initialPassword: 'Senha inicial',
      role: 'Papel',
      team: 'Equipe',
      status: 'Status',
      lastLogin: 'Último acesso',
    },
    status: {
      active: 'Ativo',
      inactive: 'Inativo',
    },
    filters: {
      search: 'Buscar por nome ou e-mail',
      allRoles: 'Todos os papéis',
      allStatuses: 'Todos os status',
    },
    actions: {
      create: 'Novo usuário',
      editUser: 'Editar {name}',
      activate: 'Ativar usuário',
      deactivate: 'Desativar usuário',
      activateUser: 'Ativar {name}',
      deactivateUser: 'Desativar {name}',
    },
    form: {
      createTitle: 'Novo usuário',
      createDescription: 'O usuário poderá entrar com este e-mail e a senha inicial.',
      editTitle: 'Editar usuário',
      noTeam: 'Sem equipe',
      passwordHelp: 'Mínimo de 8 caracteres; evite senhas comuns. Compartilhe por um canal seguro.',
      selfRoleHelp: 'Você não pode alterar o próprio papel.',
    },
    confirm: {
      deactivateTitle: 'Desativar {name}?',
      deactivateDescription:
        'A pessoa perde o acesso imediatamente, inclusive em sessões abertas. Você pode reativá-la depois.',
      activateTitle: 'Ativar {name}?',
      activateDescription: 'A pessoa voltará a acessar o OrderFlow com o papel atual.',
    },
    feedback: {
      created: 'Usuário criado.',
      updated: 'Usuário atualizado.',
      activated: 'Usuário ativado.',
      deactivated: 'Usuário desativado.',
    },
    empty: {
      title: 'Nenhum usuário cadastrado',
      description: 'Convide as pessoas da sua organização criando o primeiro usuário.',
      filteredTitle: 'Nenhum usuário encontrado',
      filteredDescription: 'Ajuste a busca ou os filtros utilizados.',
    },
    error: {
      title: 'Não foi possível carregar os usuários',
    },
  },
  teams: {
    title: 'Equipes',
    description: 'Agrupamentos de pessoas da organização.',
    memberCount: 'Nenhum membro | {count} membro | {count} membros',
    fields: {
      name: 'Nome da equipe',
    },
    actions: {
      create: 'Nova equipe',
      renameTeam: 'Renomear {name}',
    },
    form: {
      createTitle: 'Nova equipe',
      renameTitle: 'Renomear equipe',
    },
    feedback: {
      created: 'Equipe criada.',
      renamed: 'Equipe renomeada.',
    },
    empty: {
      title: 'Nenhuma equipe criada',
      description: 'Crie equipes para organizar as pessoas da sua organização.',
    },
    error: {
      title: 'Não foi possível carregar as equipes',
    },
  },
  forbidden: {
    title: 'Acesso não permitido',
    description: 'Seu papel não tem permissão para acessar esta página. Fale com um administrador.',
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
    RATE_LIMITED: 'Muitas tentativas. Aguarde um minuto e tente novamente.',
    requestId: 'Código para suporte: {requestId}',
  },
}
