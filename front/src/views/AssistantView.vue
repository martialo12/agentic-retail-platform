<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

import HumanHandoff from '@/components/socle/HumanHandoff.vue'
import SoclePanel from '@/components/socle/SoclePanel.vue'
import { useRunStore } from '@/stores/runStore'

const store = useRunStore()

// Leaving the view must not leave a run burning tokens in the background.
onBeforeUnmount(() => store.cancel())

const draft = ref('')
const asked = ref('')

/** The demo script, one click each — a presenter should never have to type. */
const examples = [
  { tag: 'commande', question: 'Où en est ma commande o002 ?' },
  { tag: 'produit', question: 'Quelles sont les caractéristiques du produit p001 ?' },
  { tag: 'remboursement', question: 'Je veux un remboursement pour ma commande o002.' },
  { tag: 'inconnue', question: 'Quel est le statut de la commande o999 ?' },
]

function ask(question: string) {
  const q = question.trim()
  if (!q || store.running) return
  asked.value = q
  draft.value = ''
  store.start('/api/assistant/ask', { question: q })
}

const thinking = computed(
  () => store.running && !store.answer && !store.escalation && !store.error,
)
const tools = computed(() => store.toolsUsed)
</script>

<template>
  <div class="view">
    <div class="split">
      <!-- Conversation -->
      <section class="convo">
        <header class="intro">
          <p class="eyebrow mb-3">
            assistant client
          </p>
          <h1 class="title display">
            Posez une question.<br>
            Regardez le socle décider.
          </h1>
          <p class="lead">
            Chaque exécution est gouvernée en direct — outils autorisés, appels
            refusés, escalade vers un humain. La bande à droite est cette
            décision, imprimée au fil de l'eau.
          </p>
        </header>

        <div class="examples">
          <button
            v-for="ex in examples"
            :key="ex.tag"
            class="chip"
            :disabled="store.running"
            @click="ask(ex.question)"
          >
            <span class="mono chip-tag">{{ ex.tag }}</span>
            <span class="chip-q">{{ ex.question }}</span>
          </button>
        </div>

        <div
          v-if="asked"
          class="thread"
        >
          <div class="turn">
            <span class="eyebrow turn-label">vous</span>
            <p class="question">
              {{ asked }}
            </p>
          </div>

          <!-- Escalation is an outcome, not a failure (FR-017). A human takes
               over, reachable by phone or WhatsApp. -->
          <div
            v-if="store.escalation"
            class="turn"
          >
            <span class="eyebrow turn-label">socle</span>
            <HumanHandoff
              :reason="store.escalation.reason"
              :question="asked"
            />
          </div>

          <div
            v-else-if="store.error"
            class="turn"
          >
            <span class="eyebrow turn-label">socle</span>
            <div class="card card--error">
              <span class="mono err-label">échec</span>
              <p class="card-body">
                {{ store.error }}
              </p>
            </div>
          </div>

          <div
            v-else-if="store.answer"
            class="turn"
          >
            <span class="eyebrow turn-label">socle</span>
            <div class="card card--answer">
              <p class="card-body">
                {{ store.answer }}
              </p>
              <p
                v-if="tools.length"
                class="tools mono"
              >
                outils : {{ tools.join(' · ') }}
              </p>
            </div>
          </div>

          <div
            v-else-if="thinking"
            class="turn"
          >
            <span class="eyebrow turn-label">socle</span>
            <p class="working mono">
              exécution en cours…
            </p>
          </div>
        </div>

        <form
          class="composer"
          @submit.prevent="ask(draft)"
        >
          <input
            v-model="draft"
            class="input mono"
            type="text"
            placeholder="Posez votre question…"
            :disabled="store.running"
            aria-label="Question"
          >
          <button
            v-if="store.running"
            type="button"
            class="btn btn--ghost"
            @click="store.cancel()"
          >
            interrompre
          </button>
          <button
            v-else
            type="submit"
            class="btn"
            :disabled="!draft.trim()"
          >
            envoyer
          </button>
        </form>
      </section>

      <!-- Live audit tape -->
      <aside class="rail-col">
        <SoclePanel
          :events="store.events"
          :running="store.running"
        />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 56px 32px 64px;
}

.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 410px;
  gap: 48px;
  align-items: start;
}

.convo {
  min-width: 0;
}

.title {
  margin: 0 0 16px;
  font-size: var(--step4);
  color: var(--ink);
}
.lead {
  margin: 0;
  max-width: 50ch;
  color: var(--ink-2);
  font-size: var(--step2);
  line-height: 1.55;
}

.examples {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 28px 0 0;
}
.chip {
  display: flex;
  flex-direction: column;
  gap: 5px;
  text-align: left;
  padding: 12px 14px;
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 4px;
  cursor: pointer;
  transition:
    border-color 130ms ease,
    background 130ms ease,
    transform 130ms ease;
}
.chip:hover:not(:disabled) {
  border-color: var(--ink);
  transform: translateY(-1px);
}
.chip:disabled {
  opacity: 0.5;
  cursor: default;
}
.chip-tag {
  font-size: var(--step-1);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}
.chip-q {
  font-size: var(--step0);
  color: var(--ink);
  line-height: 1.35;
}

.thread {
  margin: 32px 0 0;
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.turn-label {
  display: block;
  margin-bottom: 7px;
}
.question {
  margin: 0;
  font-size: var(--step2);
  line-height: 1.4;
  color: var(--ink);
}

.card {
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 18px 20px;
  background: var(--surface);
}
.card-body {
  margin: 0;
  font-size: var(--step1);
  line-height: 1.55;
  color: var(--ink);
}
.card--answer {
  border-left: 2px solid var(--ok);
}
.tools {
  margin: 12px 0 0;
  font-size: var(--step-1);
  letter-spacing: 0.06em;
  color: var(--muted);
}

.card--error {
  border-left: 2px solid var(--error);
  background: var(--error-wash);
}
.err-label {
  display: block;
  margin-bottom: 8px;
  font-size: var(--step-1);
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--error);
}

.working {
  margin: 0;
  color: var(--muted);
  font-size: var(--step0);
}

.composer {
  display: flex;
  gap: 10px;
  margin: 32px 0 0;
}
.input {
  flex: 1 1 auto;
  min-width: 0;
  padding: 12px 14px;
  font-size: var(--step1);
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--rule-strong);
  border-radius: 4px;
  transition: border-color 130ms ease;
}
.input:focus {
  outline: none;
  border-color: var(--ink);
}
.input:disabled {
  background: var(--surface-2);
  color: var(--muted);
}

.btn {
  flex: 0 0 auto;
  padding: 0 22px;
  font-family: var(--mono);
  font-size: var(--step0);
  letter-spacing: 0.08em;
  color: var(--surface);
  background: var(--ink);
  border: 1px solid var(--ink);
  border-radius: 4px;
  cursor: pointer;
  transition: opacity 130ms ease;
}
.btn:hover:not(:disabled) {
  opacity: 0.85;
}
.btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.btn--ghost {
  color: var(--ink);
  background: var(--surface);
}

.rail-col {
  position: sticky;
  top: 32px;
  height: calc(100vh - 52px - 72px);
  min-height: 440px;
}

@media (max-width: 880px) {
  .split {
    grid-template-columns: 1fr;
    gap: 28px;
  }
  .examples {
    grid-template-columns: 1fr;
  }
  .rail-col {
    position: static;
    height: 460px;
  }
}
</style>
