import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { stream, type RunEvent } from '@/services/apiClient'

/**
 * One run, reduced as its events arrive.
 *
 * The store never *decides* an outcome — it reflects what the socle emitted. A
 * refused tool call stays in `events` and is only excluded from `toolsUsed`;
 * hiding it would erase the exact thing the console exists to show.
 */
export const useRunStore = defineStore('run', () => {
  const events = ref<RunEvent[]>([])
  const running = ref(false)
  const error = ref<string | null>(null)
  const output = ref<RunEvent | null>(null)
  const escalationEvent = ref<RunEvent | null>(null)

  let abort: (() => void) | null = null

  const toolsUsed = computed(() =>
    events.value
      .filter((e) => e.kind === 'tool_call' && e.refused === false)
      .map((e) => String(e.tool)),
  )

  const refusals = computed(() =>
    events.value.filter((e) => e.kind === 'tool_call' && e.refused === true),
  )

  // Escalation is a first-class outcome, not an error. It arrives either as its
  // own event (the policy gate) or as an output marked escalated (the emit
  // node) — either is authoritative.
  const escalation = computed<{ reason: string } | null>(() => {
    const source =
      escalationEvent.value ?? (output.value?.escalated ? output.value : null)
    if (!source) return null
    return { reason: String(source.reason ?? 'transféré à un conseiller') }
  })

  const answer = computed<string | null>(() =>
    output.value?.answer != null ? String(output.value.answer) : null,
  )

  const enriched = computed<Record<string, unknown> | null>(() =>
    (output.value?.enriched as Record<string, unknown>) ?? null,
  )

  function num(value: unknown): number | null {
    return typeof value === 'number' ? value : null
  }

  // Both ride on either the output or the escalation event, so the confidence
  // rule reads the same whether the run cleared the bar or was stopped by it.
  const confidence = computed<number | null>(
    () => num(output.value?.confidence) ?? num(escalationEvent.value?.confidence),
  )
  const threshold = computed<number | null>(
    () => num(output.value?.threshold) ?? num(escalationEvent.value?.threshold),
  )

  /** The run bears a governance mark: a refusal or an escalation happened. */
  const stamped = computed(() => escalation.value !== null || refusals.value.length > 0)

  function reset() {
    abort?.()
    abort = null
    events.value = []
    running.value = false
    error.value = null
    output.value = null
    escalationEvent.value = null
  }

  function start(path: string, body: unknown) {
    reset()
    running.value = true
    abort = stream(path, body, {
      onEvent(event) {
        events.value = [...events.value, event]
        if (event.kind === 'escalation') escalationEvent.value = event
        if (event.kind === 'output') output.value = event
        if (event.kind === 'error') error.value = String(event.message ?? 'erreur inconnue')
      },
      onDone() {
        running.value = false
        abort = null
      },
      onError(message) {
        error.value = message
      },
    })
  }

  function cancel() {
    abort?.()
    abort = null
    running.value = false
  }

  return {
    events,
    running,
    error,
    output,
    toolsUsed,
    refusals,
    escalation,
    answer,
    enriched,
    confidence,
    threshold,
    stamped,
    start,
    cancel,
    reset,
  }
})
