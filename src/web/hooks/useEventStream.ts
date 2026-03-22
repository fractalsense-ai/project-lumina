import { useEffect, useRef, useState, useCallback } from 'react'

export interface SSEEvent {
  id: string
  type: string
  data: Record<string, unknown>
  timestamp: string
}

interface UseEventStreamOptions {
  token: string
  enabled?: boolean
  onEvent?: (event: SSEEvent) => void
}

function getApiBase(): string {
  return (import.meta as any).env?.VITE_LUMINA_API_BASE_URL ?? 'http://localhost:8000'
}

/**
 * Hook that connects to the SSE event stream for real-time governance events.
 * Acquires a one-time SSE token, then opens an EventSource connection.
 */
export function useEventStream({ token, enabled = true, onEvent }: UseEventStreamOptions) {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const eventSourceRef = useRef<EventSource | null>(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const clearUnread = useCallback(() => setUnreadCount(0), [])

  useEffect(() => {
    if (!enabled || !token) return

    let cancelled = false

    async function connect() {
      // Step 1: acquire SSE token
      let sseToken: string
      try {
        const res = await fetch(`${getApiBase()}/api/events/token`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) return
        const body = await res.json()
        sseToken = body.token
      } catch {
        return
      }

      if (cancelled) return

      // Step 2: open EventSource
      const es = new EventSource(
        `${getApiBase()}/api/events/stream?token=${encodeURIComponent(sseToken)}`,
      )
      eventSourceRef.current = es

      es.onopen = () => {
        if (!cancelled) setConnected(true)
      }

      es.onmessage = (e) => {
        if (cancelled) return
        try {
          const parsed: SSEEvent = JSON.parse(e.data)
          if (!parsed.id) parsed.id = `sse-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
          if (!parsed.timestamp) parsed.timestamp = new Date().toISOString()

          setEvents((prev) => {
            const next = [...prev, parsed]
            // Keep last 200 events in memory
            return next.length > 200 ? next.slice(-200) : next
          })
          setUnreadCount((c) => c + 1)
          onEventRef.current?.(parsed)
        } catch {
          // ignore unparseable messages (heartbeats are comments, not data)
        }
      }

      es.onerror = () => {
        if (!cancelled) setConnected(false)
        es.close()
        // Reconnect after 5s
        if (!cancelled) {
          setTimeout(() => {
            if (!cancelled) connect()
          }, 5000)
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      eventSourceRef.current?.close()
      eventSourceRef.current = null
      setConnected(false)
    }
  }, [token, enabled])

  return { connected, events, unreadCount, clearUnread }
}
