import { createApp } from 'vue'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'

import App from './App.vue'
import router from './router'
import pinia from './stores'
import './styles/global.scss'

const app = createApp(App)

app.use(pinia)
app.use(router)

app.mount('#app')
