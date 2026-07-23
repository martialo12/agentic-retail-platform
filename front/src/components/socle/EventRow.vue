<script setup lang="ts">
import { computed } from 'vue'

import type { RunEvent } from '@/services/apiClient'

const props = defineProps<{
  event: RunEvent
  /** A governance mark occurred on an earlier row — the spine arrives wine. */
  spineArmed?: boolean
  first?: boolean
  last?: boolean
}>()

type Tone = 'neutral' | 'ok' | 'stamp' | 'error'

interface View {
  tone: Tone
  label: string
  detail: string
  seal?: string
}

function timeOf(at: unknown): string {
  if (typeof at !== 'string') return ''
  const d = new Date(at)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('fr-FR', { hour12: false })
}

const view = computed<View>(() => {
  const e = props.event
  switch (e.kind) {
    case 'retrieval': {
      const hits = e.hits as number | undefined
      const tools = e.tools as string[] | undefined
      const detail =
        hits != null
          ? `${hits} passage${hits === 1 ? '' : 's'} récupéré${hits === 1 ? '' : 's'}`
          : tools?.length
            ? `outils pertinents : ${tools.join(', ')}`
            : 'contexte récupéré'
      return { tone: 'neutral', label: 'récupération', detail }
    }
    case 'tool_call': {
      const tool = String(e.tool ?? 'outil')
      if (e.refused === true) {
        return {
          tone: 'stamp',
          label: 'appel outil',
          detail: `${tool} — hors du périmètre autorisé`,
          seal: 'refusé',
        }
      }
      return { tone: 'ok', label: 'appel outil', detail: `${tool} — autorisé` }
    }
    case 'llm_call': {
      const attempt = e.attempt as number | undefined
      const prefix = attempt != null ? `tentative ${attempt} · ` : ''
      if (e.valid === false) {
        return {
          tone: 'neutral',
          label: 'appel modèle',
          detail: `${prefix}rejeté par le schéma${e.error ? ` : ${e.error}` : ''}`,
        }
      }
      return { tone: 'neutral', label: 'appel modèle', detail: `${prefix}schéma validé` }
    }
    case 'escalation': {
      const conf = e.confidence as number | null | undefined
      const threshold = e.threshold as number | undefined
      const measured =
        conf != null && threshold != null
          ? ` · confiance ${conf.toFixed(2)} < seuil ${threshold.toFixed(2)}`
          : ''
      return {
        tone: 'stamp',
        label: 'escalade',
        detail: `${String(e.reason ?? 'transféré à un conseiller')}${measured}`,
        seal: 'escalade',
      }
    }
    case 'output': {
      if (e.escalated === true) {
        return {
          tone: 'stamp',
          label: 'sortie',
          detail: String(e.reason ?? 'transféré à un conseiller'),
          seal: 'escalade',
        }
      }
      const conf = e.confidence as number | undefined
      return {
        tone: 'ok',
        label: 'sortie',
        detail: conf != null ? `validée · confiance ${conf.toFixed(2)}` : 'validée',
      }
    }
    case 'error':
      return { tone: 'error', label: 'erreur', detail: String(e.message ?? 'erreur inconnue') }
    default:
      return { tone: 'neutral', label: String(e.kind), detail: '' }
  }
})

const isStamp = computed(() => view.value.tone === 'stamp')
const outgoingArmed = computed(() => props.spineArmed || isStamp.value)
const time = computed(() => timeOf(props.event.at))
</script>

<template>
  <li class="row">
    <div class="rail">
      <span
        class="seg seg--top"
        :class="{ armed: spineArmed, hidden: first }"
      />
      <span
        class="marker"
        :class="`marker--${view.tone}`"
      />
      <span
        class="seg seg--bot"
        :class="{ armed: outgoingArmed, hidden: last }"
      />
    </div>

    <div class="body">
      <div class="meta">
        <span class="mono time">{{ time }}</span>
        <span
          class="mono label"
          :class="`label--${view.tone}`"
        >{{ view.label }}</span>
        <span
          v-if="view.seal"
          class="stamp seal"
        >{{ view.seal }}</span>
      </div>
      <p
        class="detail"
        :class="{ 'detail--stamp': isStamp, 'detail--error': view.tone === 'error' }"
      >
        {{ view.detail }}
      </p>
    </div>
  </li>
</template>

<style scoped>
.row {
  display: grid;
  grid-template-columns: 30px 1fr;
  column-gap: 14px;
  list-style: none;
  animation: print 200ms ease both;
}

@keyframes print {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* The rail carries the spine and the marker; the spine's two segments let the
   wine begin exactly at the marker of the row that was stamped. */
.rail {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.seg {
  width: 2px;
  background: var(--rule-strong);
  flex: 1 0 auto;
  transition: background 220ms ease;
}
.seg--top {
  min-height: 9px;
}
.seg--bot {
  min-height: 22px;
}
.seg.armed {
  background: var(--stamp);
}
.seg.hidden {
  background: transparent;
}

.marker {
  flex: 0 0 auto;
  width: 9px;
  height: 9px;
  margin: 2px 0;
  border-radius: 50%;
  background: var(--surface);
  border: 2px solid var(--rule-strong);
  z-index: 1;
}
.marker--ok {
  background: var(--ok);
  border-color: var(--ok);
  box-shadow: 0 0 0 3px var(--ok-wash);
}
.marker--error {
  background: var(--error);
  border-color: var(--error);
  box-shadow: 0 0 0 3px var(--error-wash);
}
/* A stamped event is a diamond, not a dot — it reads as *flagged*, and it is
   the only place besides the seal where the wine appears. */
.marker--stamp {
  width: 11px;
  height: 11px;
  border-radius: 2px;
  transform: rotate(45deg);
  background: var(--stamp);
  border-color: var(--stamp);
  box-shadow: 0 0 0 3px var(--stamp-wash);
}

.body {
  min-width: 0;
  padding-bottom: 18px;
}
.meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.time {
  font-size: var(--step-1);
  color: var(--muted);
  letter-spacing: 0.02em;
}
.label {
  font-size: var(--step-1);
  font-weight: 500;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--ink-2);
}
.label--ok {
  color: var(--ok);
}
.label--error {
  color: var(--error);
}
.label--stamp {
  color: var(--stamp);
}

.seal {
  transform: rotate(-1.6deg) scale(0.92);
}

.detail {
  margin: 3px 0 0;
  font-size: var(--step0);
  line-height: 1.45;
  color: var(--ink-2);
  overflow-wrap: anywhere;
}
.detail--stamp {
  color: var(--stamp-ink);
  font-weight: 500;
}
.detail--error {
  color: var(--error);
}
</style>
