import { createApp, type Plugin } from 'vue'
import './style.css'
import 'uno.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
// vue-tsc in this repository targets Vue 3.2 typings, so we cast here to keep type safety
app.use(router as unknown as Plugin)
app.mount('#app')
