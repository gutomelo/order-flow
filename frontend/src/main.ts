import '@fontsource-variable/inter'
import '@/app/styles/main.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/App.vue'
import { i18n } from '@/app/providers/i18n'
import { createAppQueryClient } from '@/app/providers/queryClient'
import { createAppRouter } from '@/app/router'

const app = createApp(App)

app.use(createPinia())
app.use(createAppRouter())
app.use(i18n)
app.use(VueQueryPlugin, { queryClient: createAppQueryClient() })

app.mount('#app')
