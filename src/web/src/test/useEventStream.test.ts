import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

import { useEventStream } from '../../hooks/useEventStream'

describe('useEventStream', () => {
  let fetchMock: ReturnType<typeof vi.fn>
  let mockEventSource: any

  beforeEach(() => {
    vi.restoreAllMocks()

    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ token: 'sse-test-token' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    // Mock EventSource
    mockEventSource = {
      onopen: null as any,
      onmessage: null as any,
      onerror: null as any,
      close: vi.fn(),
    }
    vi.stubGlobal('EventSource', vi.fn(() => mockEventSource))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts disconnected', () => {
    const { result } = renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: false }),
    )
    expect(result.current.connected).toBe(false)
    expect(result.current.events).toEqual([])
    expect(result.current.unreadCount).toBe(0)
  })

  it('fetches SSE token on connect', async () => {
    renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: true }),
    )

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/events/token'),
        expect.objectContaining({
          headers: { Authorization: 'Bearer auth-token' },
        }),
      )
    })
  })

  it('opens EventSource with SSE token', async () => {
    renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: true }),
    )

    await waitFor(() => {
      expect(EventSource).toHaveBeenCalledWith(
        expect.stringContaining('token=sse-test-token'),
      )
    })
  })

  it('sets connected true on open', async () => {
    const { result } = renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: true }),
    )

    await waitFor(() => {
      expect(mockEventSource.onopen).toBeTruthy()
    })

    act(() => {
      mockEventSource.onopen()
    })

    expect(result.current.connected).toBe(true)
  })

  it('tracks events from messages', async () => {
    const { result } = renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: true }),
    )

    await waitFor(() => {
      expect(mockEventSource.onmessage).toBeTruthy()
    })

    act(() => {
      mockEventSource.onmessage({
        data: JSON.stringify({
          id: 'evt-1',
          type: 'escalation',
          data: { trigger: 'test' },
          timestamp: '2025-01-01T00:00:00Z',
        }),
      })
    })

    expect(result.current.events).toHaveLength(1)
    expect(result.current.events[0].type).toBe('escalation')
    expect(result.current.unreadCount).toBe(1)
  })

  it('clearUnread resets count', async () => {
    const { result } = renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: true }),
    )

    await waitFor(() => {
      expect(mockEventSource.onmessage).toBeTruthy()
    })

    act(() => {
      mockEventSource.onmessage({
        data: JSON.stringify({ id: 'e1', type: 'info', data: {}, timestamp: '' }),
      })
    })
    expect(result.current.unreadCount).toBe(1)

    act(() => {
      result.current.clearUnread()
    })
    expect(result.current.unreadCount).toBe(0)
  })

  it('closes EventSource on unmount', async () => {
    const { unmount } = renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: true }),
    )

    await waitFor(() => {
      expect(EventSource).toHaveBeenCalled()
    })

    unmount()
    expect(mockEventSource.close).toHaveBeenCalled()
  })

  it('does nothing when disabled', async () => {
    renderHook(() =>
      useEventStream({ token: 'auth-token', enabled: false }),
    )

    // Give time for potential async effects
    await new Promise((r) => setTimeout(r, 50))
    expect(fetchMock).not.toHaveBeenCalled()
    expect(EventSource).not.toHaveBeenCalled()
  })
})
