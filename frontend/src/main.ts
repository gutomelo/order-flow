import '@fontsource-variable/inter'
import '@/app/styles/main.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/App.vue'
import { i18n } from '@/app/providers/i18n'
import { createAppQueryClient } from '@/app/providers/queryClient'
import { connectSessionToHttpClient } from '@/app/providers/session'
import { createAppRouter } from '@/app/router'

const app = createApp(App)
const pinia = createPinia()
const router = createAppRouter()

app.use(pinia)
connectSessionToHttpClient(pinia, router)
app.use(router)
app.use(i18n)
app.use(VueQueryPlugin, { queryClient: createAppQueryClient() })

app.mount('#app')
