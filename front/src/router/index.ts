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
  ],
})

export default router
