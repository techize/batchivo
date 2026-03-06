/**
 * WebSocket hook for live printer state from /ws/printers
 *
 * Connects on mount, reconnects automatically after 3s on disconnect.
 * Falls back to REST polling via TanStack Query when the WS is unavailable.
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { getAuthTokens } from '@/lib/auth'
import { config } from '@/lib/config'
import type { PrinterLiveState } from '@/types/printer'

const RECONNECT_DELAY_MS = 3000

function buildWsUrl(token: string): string {
  const base = config.apiUrl || window.location.origin
  // Convert http(s) → ws(s)
  const wsBase = base.replace(/^http/, 'ws')
  return `${wsBase}/ws/printers?token=${encodeURIComponent(token)}`
}

export interface UsePrinterWebSocketResult {
  printers: PrinterLiveState[]
  connected: boolean
}

export function usePrinterWebSocket(): UsePrinterWebSocketResult {
  const [printers, setPrinters] = useState<PrinterLiveState[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  const connect = useCallback(() => {
    if (unmountedRef.current) return

    const tokens = getAuthTokens()
    if (!tokens?.accessToken) return

    const url = buildWsUrl(tokens.accessToken)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!unmountedRef.current) setConnected(true)
    }

    ws.onmessage = (event) => {
      if (unmountedRef.current) return
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'printer_state' && Array.isArray(msg.data)) {
          setPrinters(msg.data)
        }
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      if (unmountedRef.current) return
      setConnected(false)
      wsRef.current = null
      // Reconnect after 3 s
      reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    unmountedRef.current = false
    connect()

    return () => {
      unmountedRef.current = true
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { printers, connected }
}
