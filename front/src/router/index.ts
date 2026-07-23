import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'assistant',
      component: () => import('@/views/AssistantView.vue'),
      meta: { label: 'assistant' },
    },
    {
      path: '/enrichissement',
      name: 'enrichissement',
      component: () => import('@/views/EnrichmentView.vue'),
      meta: { label: 'enrichissement' },
    },
    {
      path: '/observabilite',
      name: 'observabilite',
      component: () => import('@/views/ObservabilityView.vue'),
      meta: { label: 'observabilité' },
    },
  ],
})

export default router
