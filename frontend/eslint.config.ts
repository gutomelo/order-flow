import pluginVitest from '@vitest/eslint-plugin'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import skipFormatting from 'eslint-config-prettier/flat'
import { globalIgnores } from 'eslint/config'
import pluginVue from 'eslint-plugin-vue'

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,ts,mts,tsx}'],
  },

  globalIgnores(['**/dist/**', '**/coverage/**']),

  ...pluginVue.configs['flat/recommended'],
  vueTsConfigs.strict,

  {
    name: 'app/rules',
    rules: {
      // Componentes de página e layout têm nomes compostos; App.vue é a exceção natural.
      'vue/multi-word-component-names': ['error', { ignores: ['App'] }],
      'vue/block-lang': ['error', { script: { lang: 'ts' } }],
      'vue/component-api-style': ['error', ['script-setup']],
    },
  },

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/tests/**/*', 'src/**/*.spec.ts'],
  },

  // Formatação é responsabilidade do Prettier.
  skipFormatting,
)
