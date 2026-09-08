// Display face for the human voice (hero, view titles); machine testimony stays
// mono. Variable so weight and optical size stay crisp from caption to hero.
import '@fontsource-variable/bricolage-grotesque'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/500.css'
import '@fontsource/ibm-plex-sans/600.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { initAnalytics, trackPageView } from './services/analytics'
import vuetify from './plugins/vuetify'
import router from './router'
import './styles/main.scss'

initAnalytics()
// Une application a page unique ne declenche qu'une vue au chargement : les
// navigations suivantes doivent etre envoyees a la main.
router.afterEach((to) => trackPageView(to.fullPath, String(to.meta.label ?? to.name ?? '')))

createApp(App).use(createPinia()).use(router).use(vuetify).mount('#app')
