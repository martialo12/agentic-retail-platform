<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
const links = router.getRoutes().filter((route) => route.meta?.label)
</script>

<template>
  <v-app>
    <header class="topbar hairline">
      <RouterLink
        to="/"
        class="brand"
      >
        <span class="mono mark">arp</span>
        <span class="brand-sub eyebrow">console socle</span>
      </RouterLink>

      <nav class="nav">
        <RouterLink
          v-for="link in links"
          :key="link.path"
          :to="link.path"
          class="eyebrow nav-link"
        >
          {{ link.meta.label }}
        </RouterLink>
      </nav>

      <span class="eyebrow tag">gouvernance en direct</span>
    </header>

    <v-main>
      <RouterView />
    </v-main>
  </v-app>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: 36px;
  height: 52px;
  padding: 0 28px;
  background: var(--surface);
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
  text-decoration: none;
}
.mark {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--ink);
  letter-spacing: 0.04em;
}
.brand-sub {
  color: var(--muted);
}

.nav {
  display: flex;
  gap: 26px;
}
.nav-link {
  color: var(--muted);
  text-decoration: none;
  padding-bottom: 2px;
  border-bottom: 1px solid transparent;
  transition:
    color 120ms ease,
    border-color 120ms ease;
}
.nav-link:hover,
.nav-link.router-link-active {
  color: var(--ink);
  border-bottom-color: var(--ink);
}

.tag {
  margin-left: auto;
  color: var(--muted);
}

@media (max-width: 600px) {
  .topbar {
    gap: 20px;
    padding: 0 16px;
  }
  .brand-sub,
  .tag {
    display: none;
  }
}
</style>
