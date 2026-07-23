<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import SoclePanel from '@/components/socle/SoclePanel.vue'
import { getRun, listRuns, type RunRecord, type RunSummary } from '@/services/runsService'

const agents = [
  { value: '', label: 'tous' },
  { value: 'customer-assistant', label: 'assistant' },
  { value: 'product-enricher', label: 'enrichisseur' },
]
const outcomes = [
  { value: '', label: 'tous' },
  { value: 'completed', label: 'terminé' },
  { value: 'escalated', label: 'escaladé' },
  { value: 'failed', label: 'échoué' },
]

const agent = ref('')
const outcome = ref('')
const rows = ref<RunSummary[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)

const detail = ref<RunRecord | null>(null)
const detailOpen = ref(false)

async function refresh() {
  loading.value = true
  loadError.value = null
  try {
    const data = await listRuns({ agent: agent.value, outcome: outcome.value })
    rows.value = data.items
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function open(row: RunSummary) {
  detailOpen.value = true
  detail.value = null
  try {
    detail.value = await getRun(row.run_id)
  } catch {
    detailOpen.value = false
  }
}

function close() {
  detailOpen.value = false
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}

function tone(o: string): string {
  if (o === 'escalated') return 'stamp'
  if (o === 'failed') return 'error'
  return 'ok'
}

const outcomeLabel: Record<string, string> = {
  completed: 'terminé',
  escalated: 'escaladé',
  failed: 'échoué',
}

function when(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

const detailLabel = computed(() =>
  detail.value ? `run ${detail.value.run_id.slice(0, 8)}` : 'run',
)

watch([agent, outcome], refresh)
onMounted(() => {
  refresh()
  window.addEventListener('keydown', onKey)
})
</script>

<template>
  <div class="view">
    <header class="intro">
      <p class="eyebrow mb-2">
        observabilité
      </p>
      <h1 class="title">
        Chaque exécution, conservée et relisible.
      </h1>
      <p class="lead">
        Le registre indexe les runs pour la vue ; l'artefact d'audit reste le
        JSONL sur disque. Ouvrez un run pour rejouer sa bande, événement par
        événement.
      </p>
    </header>

    <div class="filters">
      <div class="filter">
        <span class="eyebrow">agent</span>
        <div class="seg">
          <button
            v-for="a in agents"
            :key="a.value"
            class="seg-btn mono"
            :class="{ on: agent === a.value }"
            @click="agent = a.value"
          >
            {{ a.label }}
          </button>
        </div>
      </div>
      <div class="filter">
        <span class="eyebrow">issue</span>
        <div class="seg">
          <button
            v-for="o in outcomes"
            :key="o.value"
            class="seg-btn mono"
            :class="{ on: outcome === o.value }"
            @click="outcome = o.value"
          >
            {{ o.label }}
          </button>
        </div>
      </div>
    </div>

    <div class="table-wrap">
      <div
        class="tr th mono"
        role="row"
      >
        <span>run</span>
        <span>agent</span>
        <span>issue</span>
        <span>fournisseur</span>
        <span class="num">événements</span>
        <span>horodatage</span>
      </div>

      <p
        v-if="loadError"
        class="state mono"
      >
        registre injoignable — lancer <code>make serve-api</code>
      </p>
      <p
        v-else-if="loading"
        class="state mono"
      >
        chargement…
      </p>
      <p
        v-else-if="rows.length === 0"
        class="state mono"
      >
        aucun run — lancez une question depuis l'assistant
      </p>

      <button
        v-for="row in rows"
        v-else
        :key="row.run_id"
        class="tr row"
        @click="open(row)"
      >
        <span class="mono cell-id">{{ row.run_id.slice(0, 8) }}</span>
        <span class="cell-agent">{{ row.agent_id }}</span>
        <span
          class="badge"
          :class="`badge--${tone(row.outcome)}`"
        >{{ outcomeLabel[row.outcome] ?? row.outcome }}</span>
        <span class="mono cell-prov">{{ row.provider ?? '—' }}</span>
        <span class="mono num">{{ row.event_count }}</span>
        <span class="mono cell-when">{{ when(row.started_at) }}</span>
      </button>
    </div>

    <!-- Detail drawer -->
    <Transition name="drawer">
      <div
        v-if="detailOpen"
        class="scrim"
        @click.self="close"
      >
        <aside
          class="drawer"
          role="dialog"
          aria-label="Détail du run"
        >
          <header class="drawer-head hairline">
            <div>
              <span class="eyebrow d-block mb-1">run</span>
              <span class="mono drawer-id">{{ detail?.run_id ?? '…' }}</span>
            </div>
            <button
              class="close mono"
              aria-label="Fermer"
              @click="close"
            >
              ✕
            </button>
          </header>

          <div class="drawer-meta">
            <span class="mono">{{ detail?.agent_id ?? '' }}</span>
            <span
              v-if="detail"
              class="badge"
              :class="`badge--${tone(detail.outcome)}`"
            >{{ outcomeLabel[detail.outcome] ?? detail.outcome }}</span>
          </div>
          <p
            v-if="detail?.error"
            class="drawer-error mono"
          >
            {{ detail.error }}
          </p>

          <div class="drawer-tape">
            <SoclePanel
              :events="detail?.events ?? []"
              :label="detailLabel"
            />
          </div>
        </aside>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.view {
  max-width: 1180px;
  margin: 0 auto;
  padding: 40px 32px 48px;
}
.title {
  margin: 0 0 12px;
  font-size: var(--step3);
  font-weight: 500;
  line-height: 1.15;
  letter-spacing: -0.01em;
}
.lead {
  margin: 0;
  max-width: 60ch;
  color: var(--ink-2);
  line-height: 1.55;
}

.filters {
  display: flex;
  gap: 28px;
  flex-wrap: wrap;
  margin: 30px 0 18px;
}
.filter {
  display: flex;
  align-items: center;
  gap: 12px;
}
.seg {
  display: inline-flex;
  border: 1px solid var(--rule-strong);
  border-radius: 4px;
  overflow: hidden;
}
.seg-btn {
  padding: 6px 12px;
  font-size: var(--step-1);
  letter-spacing: 0.06em;
  color: var(--muted);
  background: var(--surface);
  border: none;
  border-right: 1px solid var(--rule);
  cursor: pointer;
  transition:
    background 120ms ease,
    color 120ms ease;
}
.seg-btn:last-child {
  border-right: none;
}
.seg-btn:hover {
  color: var(--ink);
}
.seg-btn.on {
  background: var(--ink);
  color: var(--surface);
}

/* Ledger */
.table-wrap {
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--surface);
  overflow-x: auto;
}
.tr {
  display: grid;
  grid-template-columns: 84px minmax(140px, 1.4fr) 96px minmax(120px, 1fr) 96px minmax(150px, 1.2fr);
  align-items: center;
  gap: 16px;
  padding: 12px 18px;
  min-width: 720px;
  text-align: left;
}
.th {
  font-size: var(--step-1);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  background: var(--surface-2);
  border-bottom: 1px solid var(--rule);
}
.num {
  text-align: right;
}
.row {
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--rule);
  cursor: pointer;
  transition: background 110ms ease;
  font-size: var(--step0);
}
.row:last-child {
  border-bottom: none;
}
.row:hover {
  background: var(--surface-2);
}
.cell-id {
  color: var(--ink);
}
.cell-agent {
  color: var(--ink-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell-prov,
.cell-when {
  font-size: var(--step-1);
  color: var(--muted);
}

.badge {
  justify-self: start;
  font-family: var(--mono);
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 2px;
  border: 1px solid;
}
.badge--ok {
  color: var(--ok);
  border-color: rgba(31, 111, 92, 0.4);
  background: var(--ok-wash);
}
.badge--error {
  color: var(--error);
  border-color: rgba(138, 43, 31, 0.4);
  background: var(--error-wash);
}
.badge--stamp {
  color: var(--stamp);
  border-color: rgba(122, 31, 75, 0.4);
  background: var(--stamp-wash);
}

.state {
  padding: 28px 18px;
  font-size: var(--step0);
  color: var(--muted);
}

/* Drawer */
.scrim {
  position: fixed;
  inset: 0;
  background: rgba(20, 24, 31, 0.32);
  display: flex;
  justify-content: flex-end;
  z-index: 30;
}
.drawer {
  width: min(460px, 92vw);
  height: 100%;
  background: var(--paper);
  border-left: 1px solid var(--rule-strong);
  display: flex;
  flex-direction: column;
  padding: 20px 22px 22px;
}
.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 14px;
}
.drawer-id {
  font-size: var(--step0);
  color: var(--ink);
}
.close {
  font-size: var(--step1);
  color: var(--muted);
  background: none;
  border: none;
  cursor: pointer;
  line-height: 1;
  padding: 2px 6px;
}
.close:hover {
  color: var(--ink);
}
.drawer-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 14px 0;
  font-size: var(--step0);
  color: var(--ink-2);
}
.drawer-error {
  margin: 0 0 12px;
  font-size: var(--step-1);
  color: var(--error);
}
.drawer-tape {
  flex: 1 1 auto;
  min-height: 0;
}

.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 180ms ease;
}
.drawer-enter-active .drawer,
.drawer-leave-active .drawer {
  transition: transform 220ms ease;
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .drawer,
.drawer-leave-to .drawer {
  transform: translateX(24px);
}
</style>
