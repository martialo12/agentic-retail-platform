<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import SoclePanel from '@/components/socle/SoclePanel.vue'
import { get } from '@/services/apiClient'
import { useRunStore } from '@/stores/runStore'

interface Sheet {
  id: string
  title: string
  specs: Record<string, string>
  category: string | null
}

interface Enriched {
  category: string
  seo_description: string
  materials: string[]
  use_cases: string[]
  confidence: number
}

const store = useRunStore()

const sheets = ref<Sheet[]>([])
const loadError = ref<string | null>(null)
const selectedId = ref<string | null>(null)

const selected = computed(() => sheets.value.find((s) => s.id === selectedId.value) ?? null)
const beforeSpecs = computed(() => Object.entries(selected.value?.specs ?? {}))

const enriched = computed(() => (store.enriched as Enriched | null) ?? null)
const materials = computed(() => enriched.value?.materials ?? [])
const useCases = computed(() => enriched.value?.use_cases ?? [])

const confidence = computed(() => store.confidence)
const threshold = computed(() => store.threshold)
const cleared = computed(
  () => confidence.value != null && threshold.value != null && confidence.value >= threshold.value,
)
const pct = (v: number | null) => `${Math.round((v ?? 0) * 100)}%`

onMounted(async () => {
  store.reset()
  try {
    const data = await get<{ items: Sheet[] }>('/api/catalogue')
    sheets.value = data.items
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
  }
})

onBeforeUnmount(() => store.reset())

function enrich(sheet: Sheet) {
  if (store.running) return
  selectedId.value = sheet.id
  store.start('/api/enricher/enrich', { product_id: sheet.id })
}
</script>

<template>
  <div class="view">
    <header class="intro">
      <p class="eyebrow mb-2">
        enrichissement produit
      </p>
      <h1 class="title">
        Une fiche brute, réécrite — mais seulement si le modèle est sûr.
      </h1>
      <p class="lead">
        L'agent complète la fiche, puis le socle compare sa confiance au seuil de
        la spec. Sous le seuil, rien n'est écrit : la fiche part en relecture
        humaine.
      </p>
    </header>

    <div class="split">
      <!-- Catalogue -->
      <aside class="catalogue">
        <div class="cat-head hairline">
          <span class="eyebrow">catalogue</span>
          <span class="mono count">{{ sheets.length }}</span>
        </div>
        <p
          v-if="loadError"
          class="cat-error mono"
        >
          catalogue injoignable — lancer <code>make serve-api</code>
        </p>
        <ul class="cat-list">
          <li
            v-for="sheet in sheets"
            :key="sheet.id"
          >
            <button
              class="cat-row"
              :class="{ active: sheet.id === selectedId }"
              :disabled="store.running"
              @click="enrich(sheet)"
            >
              <span class="cat-main">
                <span class="mono cat-id">{{ sheet.id }}</span>
                <span class="cat-title">{{ sheet.title }}</span>
              </span>
              <span
                v-if="Object.keys(sheet.specs).length === 0"
                class="mono cat-flag"
              >incomplète</span>
            </button>
          </li>
        </ul>
      </aside>

      <!-- Before / after + tape -->
      <section class="work">
        <div
          v-if="!selected"
          class="placeholder"
        >
          <span class="eyebrow d-block mb-2">avant · après</span>
          Choisissez une fiche pour lancer l'enrichissement et voir le socle
          l'accepter ou la refuser.
        </div>

        <template v-else>
          <div class="diff">
            <article class="pane">
              <span class="eyebrow pane-label">avant</span>
              <h2 class="pane-title">
                {{ selected.title }}
              </h2>
              <dl
                v-if="beforeSpecs.length"
                class="specs"
              >
                <template
                  v-for="[k, v] in beforeSpecs"
                  :key="k"
                >
                  <dt class="mono">
                    {{ k }}
                  </dt>
                  <dd>{{ v }}</dd>
                </template>
              </dl>
              <p
                v-else
                class="void"
              >
                aucune spécification
              </p>
            </article>

            <article
              class="pane pane--after"
              :class="{ 'pane--muted': !enriched }"
            >
              <span class="eyebrow pane-label">après</span>
              <template v-if="enriched">
                <h2 class="pane-title">
                  {{ enriched.category }}
                </h2>
                <p class="seo">
                  {{ enriched.seo_description }}
                </p>
                <div
                  v-if="materials.length"
                  class="tags"
                >
                  <span class="tags-label mono">matières</span>
                  <span
                    v-for="m in materials"
                    :key="m"
                    class="tag"
                  >{{ m }}</span>
                </div>
                <div
                  v-if="useCases.length"
                  class="tags"
                >
                  <span class="tags-label mono">usages</span>
                  <span
                    v-for="u in useCases"
                    :key="u"
                    class="tag"
                  >{{ u }}</span>
                </div>
              </template>
              <p
                v-else-if="store.escalation"
                class="void"
              >
                aucune écriture — fiche non enrichie
              </p>
              <p
                v-else
                class="void"
              >
                {{ store.running ? 'rédaction en cours…' : '—' }}
              </p>
            </article>
          </div>

          <!-- The confidence rule, made visible. -->
          <div
            v-if="confidence != null"
            class="gauge"
            :class="{ below: !cleared }"
          >
            <div class="gauge-head">
              <span class="mono gauge-conf">confiance {{ confidence.toFixed(2) }}</span>
              <span
                v-if="store.escalation"
                class="stamp"
              >relecture humaine</span>
              <span
                v-else
                class="mono gauge-ok"
              >publiée</span>
            </div>
            <div class="track">
              <div
                class="fill"
                :style="{ width: pct(confidence) }"
              />
              <div
                v-if="threshold != null"
                class="mark"
                :style="{ left: pct(threshold) }"
              >
                <span class="mono mark-label">seuil {{ threshold.toFixed(2) }}</span>
              </div>
            </div>
          </div>

          <div class="tape-wrap">
            <SoclePanel
              :events="store.events"
              :running="store.running"
            />
          </div>
        </template>
      </section>
    </div>
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
  font-family: var(--display);
  font-size: var(--step3);
  font-weight: 600;
  line-height: 1.1;
  letter-spacing: -0.02em;
  max-width: 26ch;
}
.lead {
  margin: 0;
  max-width: 56ch;
  color: var(--ink-2);
  line-height: 1.55;
}

.split {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 32px;
  margin: 32px 0 0;
  align-items: start;
}

/* Catalogue */
.catalogue {
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--surface);
  overflow: hidden;
}
.cat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 16px;
  background: var(--surface-2);
}
.count {
  font-size: var(--step0);
  color: var(--muted);
}
.cat-error {
  padding: 16px;
  font-size: var(--step0);
  color: var(--error);
}
.cat-list {
  margin: 0;
  padding: 0;
  list-style: none;
  max-height: 62vh;
  overflow-y: auto;
}
.cat-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 16px;
  text-align: left;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--rule);
  cursor: pointer;
  transition: background 120ms ease;
}
.cat-row:hover:not(:disabled) {
  background: var(--surface-2);
}
.cat-row.active {
  background: var(--stamp-wash);
  box-shadow: inset 2px 0 0 var(--stamp);
}
.cat-row:disabled {
  cursor: default;
}
.cat-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.cat-id {
  font-size: var(--step-1);
  color: var(--muted);
  letter-spacing: 0.04em;
}
.cat-title {
  font-size: var(--step0);
  color: var(--ink);
  line-height: 1.3;
}
.cat-flag {
  flex: 0 0 auto;
  font-size: 0.625rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  border: 1px solid var(--rule-strong);
  border-radius: 2px;
  padding: 2px 5px;
}

/* Work area */
.work {
  min-width: 0;
}
.placeholder {
  border: 1px dashed var(--rule-strong);
  border-radius: 4px;
  padding: 40px 28px;
  max-width: 46ch;
  color: var(--muted);
  font-size: var(--step0);
  line-height: 1.6;
}

.diff {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.pane {
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 20px;
  background: var(--surface);
}
.pane--after {
  border-left: 2px solid var(--ok);
}
.pane--muted {
  border-left-color: var(--rule-strong);
}
.pane-label {
  display: block;
  margin-bottom: 10px;
}
.pane-title {
  margin: 0 0 12px;
  font-size: var(--step2);
  font-weight: 500;
  line-height: 1.25;
}
.specs {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 16px;
  margin: 0;
  font-size: var(--step0);
}
.specs dt {
  color: var(--muted);
  font-size: var(--step-1);
}
.specs dd {
  margin: 0;
  color: var(--ink);
}
.void {
  margin: 8px 0 0;
  font-family: var(--mono);
  font-size: var(--step0);
  color: var(--muted);
}
.seo {
  margin: 0 0 14px;
  font-size: var(--step0);
  line-height: 1.55;
  color: var(--ink-2);
}
.tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}
.tags-label {
  font-size: var(--step-1);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-right: 2px;
}
.tag {
  font-size: var(--step-1);
  color: var(--ink);
  background: var(--surface-2);
  border: 1px solid var(--rule);
  border-radius: 2px;
  padding: 3px 8px;
}

/* Confidence gauge */
.gauge {
  margin: 20px 0 0;
  padding: 16px 18px;
  border: 1px solid var(--rule);
  border-radius: 4px;
  background: var(--surface);
}
.gauge.below {
  background: var(--stamp-wash);
  border-color: rgba(180, 83, 10, 0.35);
}
.gauge-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.gauge-conf {
  font-size: var(--step0);
  color: var(--ink);
}
.gauge-ok {
  font-size: var(--step-1);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ok);
}
.track {
  position: relative;
  height: 8px;
  background: var(--surface-2);
  border: 1px solid var(--rule);
  border-radius: 4px;
}
.fill {
  height: 100%;
  background: var(--ok);
  border-radius: 4px 0 0 4px;
  transition: width 400ms ease;
}
.gauge.below .fill {
  background: var(--stamp);
}
.mark {
  position: absolute;
  top: -5px;
  bottom: -5px;
  width: 2px;
  background: var(--ink);
}
.mark-label {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
  font-size: 0.625rem;
  letter-spacing: 0.08em;
  color: var(--muted);
}

.tape-wrap {
  margin: 20px 0 0;
  height: 340px;
}

@media (max-width: 880px) {
  .split {
    grid-template-columns: 1fr;
  }
  .diff {
    grid-template-columns: 1fr;
  }
}
</style>
