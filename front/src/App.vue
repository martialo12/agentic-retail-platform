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

      <span class="tag eyebrow">
        <span class="live-dot" />
        gouvernance en direct
      </span>
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
  height: var(--topbar-h);
  padding: 0 32px;
  background: color-mix(in srgb, var(--surface) 82%, transparent);
  backdrop-filter: saturate(1.2) blur(8px);
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
  text-decoration: none;
}
.mark {
  font-weight: 700;
  font-size: 1rem;
  color: var(--ink);
  letter-spacing: 0.02em;
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
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
}
.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 0 3px var(--ok-wash);
  animation: live 2s ease-in-out infinite;
}
@keyframes live {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
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
