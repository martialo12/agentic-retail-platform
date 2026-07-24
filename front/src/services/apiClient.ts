const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export interface RunEvent {
  kind: string
  at?: string
  [key: string]: unknown
}

export async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`)
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
  return (await response.json()) as T
}

/**
 * Consume a Server-Sent Events run.
 *
 * `EventSource` cannot POST, so this reads the body stream by hand. The returned
 * function aborts the request — the API cancels the run when the client leaves,
 * so abandoning a stream must not keep burning tokens.
 */
export function stream(
  path: string,
  body: unknown,
  handlers: {
    onEvent: (event: RunEvent) => void
    onDone: () => void
    onError: (message: string) => void
  },
): () => void {
  const controller = new AbortController()

  void (async () => {
    try {
      const response = await fetch(`${BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!response.ok || !response.body) {
        handlers.onError(`${response.status} ${response.statusText}`)
        handlers.onDone()
        return
      }

      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
      let buffer = ''
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += value
        // Frames are separated by a blank line; a partial frame stays buffered
        // until the rest of it arrives.
        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''
        for (const frame of frames) {
          const payload = frame.replace(/^data: /, '').trim()
          if (!payload) continue
          if (payload === '[DONE]') {
            handlers.onDone()
            return
          }
          handlers.onEvent(JSON.parse(payload) as RunEvent)
        }
      }
      handlers.onDone()
    } catch (error) {
      if (!controller.signal.aborted) {
        handlers.onError(error instanceof Error ? error.message : String(error))
        handlers.onDone()
      }
    }
  })()

  return () => controller.abort()
}



