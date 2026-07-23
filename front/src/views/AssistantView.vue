<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { get } from '@/services/apiClient'

const reachable = ref<boolean | null>(null)

onMounted(async () => {
  try {
    await get<{ status: string }>('/api/health')
    reachable.value = true
  } catch {
    reachable.value = false
  }
})
</script>

<template>
  <div class="pa-8">
    <p class="eyebrow mb-2">
      socle
    </p>
    <h1 class="text-h5 font-weight-medium mb-4">
      Console
    </h1>
    <p
      v-if="reachable === null"
      class="mono text-body-2"
    >
      connexion…
    </p>
    <p
      v-else-if="reachable"
      class="mono text-body-2"
    >
      api joignable
    </p>
    <p
      v-else
      class="mono text-body-2"
    >
      api injoignable — lancer <code>make serve-api</code>
    </p>
  </div>
</template>
