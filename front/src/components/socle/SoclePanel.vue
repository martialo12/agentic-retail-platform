<script setup lang="ts">
import { computed } from 'vue'

import EventRow from './EventRow.vue'
import type { RunEvent } from '@/services/apiClient'

const props = withDefaults(
  defineProps<{
    events: RunEvent[]
    running?: boolean
    /** Shown as the panel's eyebrow. The socle's testimony, whatever feeds it. */
    label?: string
  }>(),
  { running: false, label: 'socle' },
)

function isStampEvent(e: RunEvent): boolean {
  return (
    (e.kind === 'tool_call' && e.refused === true) ||
    e.kind === 'escalation' ||
    (e.kind === 'output' && e.escalated === true)
  )
}

const rows = computed(() =>
  props.events.map((event, i) => ({
    event,
    key: `${event.kind}-${i}`,
    spineArmed: props.events.slice(0, i).some(isStampEvent),
    first: i === 0,
    last: i === props.events.length - 1,
  })),
)

const stamped = computed(() => props.events.some(isStampEvent))
const errored = computed(() => props.events.some((e) => e.kind === 'error'))

type Status = { tone: 'idle' | 'running' | 'ok' | 'stamp' | 'error'; text: string }

const status = computed<Status>(() => {
  if (props.running) return { tone: 'running', text: 'en cours' }
  if (props.events.length === 0) return { tone: 'idle', text: 'en attente' }
  if (errored.value) return { tone: 'error', text: 'échec' }
  if (stamped.value) return { tone: 'stamp', text: 'marqué' }
  return { tone: 'ok', text: 'terminé' }
})
</script>

<template>
  <section class="panel">
    <header class="head hairline">
      <span class="eyebrow">{{ label }}</span>
      <span
        class="status"
        :class="`status--${status.tone}`"
      >
        <span class="dot" />
        <span class="mono status-text">{{ status.text }}</span>
      </span>
    </header>

    <div class="tape">
      <p
        v-if="rows.length === 0"
        class="empty"
      >
        <span class="eyebrow d-block mb-2">bande d'audit</span>
        Chaque décision du socle — récupération, appel d'outil, refus, escalade —
        s'imprimera ici au fil de l'exécution.
      </p>

      <TransitionGroup
        v-else
        tag="ul"
        name="tape"
        class="list"
      >
        <EventRow
          v-for="row in rows"
          :key="row.key"
          :event="row.event"
          :spine-armed="row.spineArmed"
          :first="row.first"
          :last="row.last"
        />
      </TransitionGroup>
    </div>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 4px;
  overflow: hidden;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: var(--surface-2);
}

.status {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.status-text {
  font-size: var(--step-1);
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--muted);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--rule-strong);
}
.status--running .dot {
  background: var(--ink);
  animation: pulse 1.1s ease-in-out infinite;
}
.status--running .status-text {
  color: var(--ink);
}
.status--ok .dot {
  background: var(--ok);
}
.status--ok .status-text {
  color: var(--ok);
}
.status--error .dot {
  background: var(--error);
}
.status--error .status-text {
  color: var(--error);
}
.status--stamp .dot {
  background: var(--stamp);
  border-radius: 1px;
  transform: rotate(45deg);
}
.status--stamp .status-text {
  color: var(--stamp);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

.tape {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 20px 18px 8px;
}

.empty {
  max-width: 34ch;
  margin: 8px 0 0;
  font-size: var(--step0);
  line-height: 1.6;
  color: var(--muted);
}

.list {
  margin: 0;
  padding: 0;
}

/* New rows slide in as the tape advances; leaving rows never animate (a run is
   reset wholesale, not trimmed). */
.tape-enter-active {
  transition:
    opacity 200ms ease,
    transform 200ms ease;
}
.tape-enter-from {
  opacity: 0;
  transform: translateY(5px);
}
</style>
