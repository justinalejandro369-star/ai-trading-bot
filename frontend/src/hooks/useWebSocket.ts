import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Signal, Candle } from '@/types'

export function useWebSocket(url: string) {
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as {
            type: string
            signal?: Signal
            symbol?: string
            candle?: Candle
          }
          if (msg.type === 'signal_update' && msg.signal) {
            queryClient.setQueryData(
              ['signals', 'top'],
              (old: Signal[] | undefined) =>
                [msg.signal as Signal, ...(old ?? [])].slice(0, 10),
            )
          }
          if (msg.type === 'price_tick' && msg.symbol && msg.candle) {
            queryClient.setQueryData(
              ['candles', msg.symbol],
              (old: Candle[] | undefined) =>
                old
                  ? [...old.slice(-199), msg.candle as Candle]
                  : [msg.candle as Candle],
            )
          }
          // 'ping' type: no-op keepalive
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = (event) => {
        if (!event.wasClean) {
          retryRef.current = setTimeout(connect, 3000)
        }
      }
    }

    connect()
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close(1000, 'component unmount')
    }
  }, [url, queryClient])
}
