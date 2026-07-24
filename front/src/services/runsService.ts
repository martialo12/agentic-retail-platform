import { get, type RunEvent } from './apiClient'

export interface RunSummary {
  run_id: string
  agent_id: string
  provider: string | null
  started_at: string
  outcome: string
  escalated: boolean
  event_count: number
}

export interface RunRecord {
  run_id: string
  agent_id: string
  provider: string | null
  timestamp: string
  outcome: string
  error: string | null
  events: RunEvent[]
}

export interface RunFilters {
  agent?: string
  outcome?: string
  limit?: number
  offset?: number
}

export function listRuns(filters: RunFilters = {}): Promise<{ items: RunSummary[]; total: number }> {
  const params = new URLSearchParams()
  if (filters.agent) params.set('agent', filters.agent)
  if (filters.outcome) params.set('outcome', filters.outcome)
  params.set('limit', String(filters.limit ?? 50))
  params.set('offset', String(filters.offset ?? 0))
  return get(`/api/runs?${params.toString()}`)
}

export function getRun(runId: string): Promise<RunRecord> {
  return get(`/api/runs/${runId}`)
}
