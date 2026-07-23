<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
const links = router.getRoutes().filter((route) => route.meta?.label)
</script>

<template>
  <v-app>
    <header
      class="hairline d-flex align-center px-6"
      style="height: 52px; background: #fff"
    >
      <span class="mono font-weight-medium mr-8">arp</span>
      <nav class="d-flex ga-6">
        <RouterLink
          v-for="link in links"
          :key="link.path"
          :to="link.path"
          class="eyebrow text-decoration-none nav-link"
        >
          {{ link.meta.label }}
        </RouterLink>
      </nav>
    </header>
    <v-main>
      <RouterView />
    </v-main>
  </v-app>
</template>

<style scoped>
.nav-link {
  color: var(--muted);
  padding-bottom: 2px;
  border-bottom: 1px solid transparent;
  transition: color 120ms ease, border-color 120ms ease;
}
.nav-link:hover,
.nav-link.router-link-active {
  color: var(--ink);
  border-bottom-color: var(--ink);
}
</style>
