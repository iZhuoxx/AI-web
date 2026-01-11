import { createApp, type Plugin } from 'vue'
import './style.css'
import 'uno.css'
import App from './App.vue'
import router from './router'
import { initAiConfig } from '@/composables/aiConfig'

const app = createApp(App)
app.use(router as unknown as Plugin)
initAiConfig().finally(() => {
  app.mount('#app')
})
