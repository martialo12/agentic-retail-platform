<script setup lang="ts">
import { computed } from 'vue'

/**
 * The handoff moment: the socle stepped out, a person steps in. This is an
 * outcome, not a failure — the copy and the calm reassure rather than apologise.
 * Two peer actions, because a customer reaches a human however they prefer.
 */
const props = defineProps<{
  /** Why the socle handed off — shown as the machine's short note. */
  reason?: string
  /** The customer's original question, carried into the WhatsApp draft so the
   *  human arrives with context instead of a cold "bonjour". */
  question?: string
}>()

// International, no spaces, no leading zero — wa.me and tel: both want it raw.
const RAW = '33753149032'
const DISPLAY = '+33 7 53 14 90 32'

const telHref = `tel:+${RAW}`

const whatsappHref = computed(() => {
  const q = props.question?.trim()
  const message = q
    ? `Bonjour, j'ai besoin d'aide concernant ma demande : « ${q} »`
    : "Bonjour, j'ai besoin d'aide concernant ma demande."
  return `https://wa.me/${RAW}?text=${encodeURIComponent(message)}`
})
</script>

<template>
  <div class="handoff">
    <span class="stamp">transféré à un humain</span>

    <p class="lede">
      Cette demande sort du périmètre de l'assistant. Un conseiller prend le
      relais — joignez-le directement, il a le contexte de votre échange.
    </p>

    <p
      v-if="reason"
      class="reason mono"
    >
      {{ reason }}
    </p>

    <div class="actions">
      <a
        class="action action--whatsapp"
        :href="whatsappHref"
        target="_blank"
        rel="noopener noreferrer"
      >
        <svg
          class="glyph"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            fill="currentColor"
            d="M12.04 2c-5.46 0-9.9 4.44-9.9 9.9 0 1.75.46 3.45 1.32 4.95L2 22l5.28-1.38a9.9 9.9 0 0 0 4.76 1.21h.01c5.46 0 9.9-4.44 9.9-9.9 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Zm0 1.8c2.16 0 4.19.84 5.72 2.37a8.06 8.06 0 0 1 2.37 5.73c0 4.47-3.63 8.1-8.1 8.1a8.1 8.1 0 0 1-4.13-1.13l-.3-.18-3.13.82.84-3.05-.2-.31a8.05 8.05 0 0 1-1.24-4.3c0-4.46 3.63-8.09 8.1-8.09Zm-2.7 4.35c-.13 0-.34.05-.52.24-.18.2-.69.68-.69 1.65 0 .97.71 1.91.81 2.05.1.13 1.39 2.22 3.44 3.02 1.7.67 2.05.54 2.42.5.37-.03 1.2-.49 1.36-.96.17-.47.17-.88.12-.96-.05-.08-.18-.13-.38-.23-.2-.1-1.2-.59-1.38-.66-.19-.07-.32-.1-.46.1-.13.2-.53.66-.65.8-.12.13-.24.15-.44.05-.2-.1-.85-.31-1.62-1-.6-.53-1-1.19-1.12-1.39-.12-.2-.01-.31.09-.41.09-.09.2-.24.3-.36.1-.12.13-.2.2-.34.06-.13.03-.25-.02-.35-.05-.1-.45-1.1-.62-1.5-.16-.4-.33-.34-.45-.34l-.39-.01Z"
          />
        </svg>
        <span class="action-body">
          <span class="action-label">Écrire sur WhatsApp</span>
          <span class="mono action-sub">{{ DISPLAY }}</span>
        </span>
      </a>

      <a
        class="action action--call"
        :href="telHref"
      >
        <svg
          class="glyph"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            fill="currentColor"
            d="M6.62 10.79a15.53 15.53 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.02-.24c1.12.37 2.33.57 3.57.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.24.2 2.45.57 3.57a1 1 0 0 1-.25 1.02l-2.2 2.2Z"
          />
        </svg>
        <span class="action-body">
          <span class="action-label">Appeler un conseiller</span>
          <span class="mono action-sub">{{ DISPLAY }}</span>
        </span>
      </a>
    </div>
  </div>
</template>

<style scoped>
.handoff {
  border: 1px solid rgba(180, 83, 10, 0.32);
  border-radius: 6px;
  padding: 20px 22px 22px;
  background:
    linear-gradient(180deg, var(--stamp-wash) 0%, var(--surface) 46%);
  box-shadow: var(--shadow-card);
}

.lede {
  margin: 16px 0 0;
  font-size: var(--step1);
  line-height: 1.6;
  color: var(--ink);
  max-width: 46ch;
}

.reason {
  margin: 10px 0 0;
  font-size: var(--step0);
  color: var(--stamp-ink);
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 20px 0 0;
}

.action {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 13px 15px;
  border-radius: 5px;
  text-decoration: none;
  transition:
    transform 130ms ease,
    box-shadow 130ms ease,
    border-color 130ms ease,
    background 130ms ease;
}
.action:hover {
  transform: translateY(-1px);
}

/* WhatsApp is the primary path — filled in the brand green (the "system working"
   thread), never WhatsApp's own green, so the palette stays disciplined. */
.action--whatsapp {
  background: var(--ok);
  color: #fff;
  box-shadow: 0 8px 20px -12px rgba(22, 98, 75, 0.7);
}
.action--whatsapp:hover {
  background: var(--ok-ink);
}

/* Calling is the calm secondary — outlined ink on paper. */
.action--call {
  background: var(--surface);
  color: var(--ink);
  border: 1px solid var(--rule-strong);
}
.action--call:hover {
  border-color: var(--ink);
}

.glyph {
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
}

.action-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.action-label {
  font-size: var(--step0);
  font-weight: 600;
  letter-spacing: 0.01em;
}
.action-sub {
  font-size: var(--step-1);
  letter-spacing: 0.04em;
  opacity: 0.82;
}

@media (max-width: 520px) {
  .actions {
    grid-template-columns: 1fr;
  }
}
</style>
