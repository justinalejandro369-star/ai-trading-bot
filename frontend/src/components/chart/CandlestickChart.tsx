import { useEffect, useRef, useState } from 'react'
import {
  createChart,
  ColorType,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickSeriesOptions,
} from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import { getCandles } from '@/api/market'
import type { Candle } from '@/types'

const WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'BTC-USD', 'ETH-USD']

export default function CandlestickChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const [symbol, setSymbol] = useState('AAPL')

  const { data: candles = [] } = useQuery<Candle[]>({
    queryKey: ['candles', symbol],
    queryFn: () => getCandles(symbol),
    staleTime: 60_000,
  })

  // Create chart once on mount
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      width: containerRef.current.clientWidth,
      height: 360,
      timeScale: { borderColor: '#334155' },
    })
    chartRef.current = chart

    // v5 API: addSeries(CandlestickSeries, options)
    const cs = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    } as Partial<CandlestickSeriesOptions>)
    candleSeriesRef.current = cs

    // RSI sub-pane on pane index 1 (v5: third arg is paneIndex number)
    chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1 }, 1)

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  // Update candle data when candles change
  useEffect(() => {
    if (candleSeriesRef.current && candles.length > 0) {
      candleSeriesRef.current.setData(
        candles.map((c) => ({
          time: c.time as import('lightweight-charts').Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        })),
      )
    }
  }, [candles])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <label htmlFor="symbol-select" className="text-slate-400 text-sm">
          Symbol
        </label>
        <select
          id="symbol-select"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="bg-slate-800 border border-slate-600 text-slate-100 text-sm rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {WATCHLIST.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />
    </div>
  )
}
