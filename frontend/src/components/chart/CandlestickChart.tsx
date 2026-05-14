import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  ColorType,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickSeriesOptions,
  type SeriesType,
} from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import { getCandles } from '@/api/market'
import { getTopSignals } from '@/api/signals'
import { useChartOverlays } from '@/hooks/useChartOverlays'
import { useChartOverlayStore } from '@/store/chartOverlays'
import {
  addEmaSeries,
  addBollingerBands,
  addRsiPane,
  addMacdPane,
  addVolumeSeries,
  addFibonacciLevels,
  addTrendLines,
  addSRLevels,
  addPivotPoints,
  addSignalMarkers,
} from './overlays/seriesManager'
import type { Candle, Signal } from '@/types'

const WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'BTC-USD', 'ETH-USD']

export default function CandlestickChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  // Track active overlay series for cleanup when toggled off
  const overlaySeriesRef = useRef<Map<string, ISeriesApi<SeriesType>[]>>(new Map())
  const [symbol, setSymbol] = useState('AAPL')

  const overlayState = useChartOverlayStore()

  const { data: candles = [] } = useQuery<Candle[]>({
    queryKey: ['candles', symbol],
    queryFn: () => getCandles(symbol),
    staleTime: 60_000,
  })

  // Fetch signals for signal markers overlay
  const { data: signals = [] } = useQuery<Signal[]>({
    queryKey: ['signals'],
    queryFn: () => getTopSignals(50),
    staleTime: 60_000,
    enabled: overlayState.showSignalMarkers,
  })

  // Fetch overlay data (indicator series + chart analysis) gated by toggle state
  const { indicatorSeries, chartAnalysis } = useChartOverlays(symbol, '1D', 200)

  /**
   * Remove all series tracked under a given overlay key.
   * PriceLines are removed by removing and re-adding the candle series data,
   * since TradingView v5 doesn't have a removePriceLine API. We handle this
   * by recreating the chart when fib/SR/pivot toggles change.
   */
  const removeOverlaySeries = useCallback((key: string) => {
    const chart = chartRef.current
    if (!chart) return
    const series = overlaySeriesRef.current.get(key)
    if (series) {
      for (const s of series) {
        try {
          chart.removeSeries(s)
        } catch {
          // Series may already be removed if chart was recreated
        }
      }
      overlaySeriesRef.current.delete(key)
    }
  }, [])

  // Create chart once on mount
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#111417' },
        textColor: '#C3C6D7',
      },
      grid: {
        vertLines: { color: '#1D2023' },
        horzLines: { color: '#1D2023' },
      },
      width: containerRef.current.clientWidth,
      height: 360,
      timeScale: { borderColor: '#424654' },
    })
    chartRef.current = chart

    // v5 API: addSeries(CandlestickSeries, options)
    const cs = chart.addSeries(CandlestickSeries, {
      upColor: '#44E092',
      downColor: '#FF5451',
      borderVisible: false,
      wickUpColor: '#44E092',
      wickDownColor: '#FF5451',
    } as Partial<CandlestickSeriesOptions>)
    candleSeriesRef.current = cs

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

  // ---------- Overlay Management ----------
  // Each overlay type gets its own useEffect that adds/removes series
  // based on toggle state and data availability.

  // EMA overlays
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !indicatorSeries) return
    removeOverlaySeries('ema')
    if (overlayState.showEma50 || overlayState.showEma200) {
      // Filter the data based on which EMAs are toggled
      const filteredData = {
        ...indicatorSeries,
        ema_50: overlayState.showEma50 ? indicatorSeries.ema_50 : indicatorSeries.ema_50.map(() => null),
        ema_200: overlayState.showEma200 ? indicatorSeries.ema_200 : indicatorSeries.ema_200.map(() => null),
      }
      const series = addEmaSeries(chart, filteredData)
      overlaySeriesRef.current.set('ema', series)
    }
    return () => removeOverlaySeries('ema')
  }, [overlayState.showEma50, overlayState.showEma200, indicatorSeries, removeOverlaySeries])

  // Bollinger Bands
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !indicatorSeries) return
    removeOverlaySeries('bb')
    if (overlayState.showBollingerBands) {
      const series = addBollingerBands(chart, indicatorSeries)
      overlaySeriesRef.current.set('bb', series)
    }
    return () => removeOverlaySeries('bb')
  }, [overlayState.showBollingerBands, indicatorSeries, removeOverlaySeries])

  // RSI sub-pane
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !indicatorSeries) return
    removeOverlaySeries('rsi')
    if (overlayState.showRsi) {
      const series = addRsiPane(chart, indicatorSeries)
      overlaySeriesRef.current.set('rsi', series)
    }
    return () => removeOverlaySeries('rsi')
  }, [overlayState.showRsi, indicatorSeries, removeOverlaySeries])

  // MACD sub-pane
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !indicatorSeries) return
    removeOverlaySeries('macd')
    if (overlayState.showMacd) {
      const series = addMacdPane(chart, indicatorSeries)
      overlaySeriesRef.current.set('macd', series)
    }
    return () => removeOverlaySeries('macd')
  }, [overlayState.showMacd, indicatorSeries, removeOverlaySeries])

  // Volume
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !indicatorSeries) return
    removeOverlaySeries('volume')
    if (overlayState.showVolume) {
      const series = addVolumeSeries(chart, indicatorSeries)
      overlaySeriesRef.current.set('volume', series)
    }
    return () => removeOverlaySeries('volume')
  }, [overlayState.showVolume, indicatorSeries, removeOverlaySeries])

  // Trend lines
  useEffect(() => {
    const chart = chartRef.current
    if (!chart || !chartAnalysis) return
    removeOverlaySeries('trendlines')
    if (overlayState.showTrendlines) {
      const series = addTrendLines(chart, chartAnalysis)
      overlaySeriesRef.current.set('trendlines', series)
    }
    return () => removeOverlaySeries('trendlines')
  }, [overlayState.showTrendlines, chartAnalysis, removeOverlaySeries])

  // Fibonacci, S/R, Pivots, and Signal markers are PriceLines on the candle series.
  // They get cleared when candle data is reset (symbol change) and re-applied here.
  useEffect(() => {
    const cs = candleSeriesRef.current
    if (!cs || !chartAnalysis) return

    if (overlayState.showFibonacci) {
      addFibonacciLevels(cs, chartAnalysis)
    }
    if (overlayState.showSupportResistance) {
      addSRLevels(cs, chartAnalysis)
    }
    if (overlayState.showPivotPoints) {
      addPivotPoints(cs, chartAnalysis)
    }
  }, [
    overlayState.showFibonacci,
    overlayState.showSupportResistance,
    overlayState.showPivotPoints,
    chartAnalysis,
    candles, // re-apply after candle data changes (price lines reset on setData)
  ])

  // Signal markers
  useEffect(() => {
    const cs = candleSeriesRef.current
    if (!cs) return

    if (overlayState.showSignalMarkers && signals.length > 0) {
      // Filter signals for the current symbol
      const symbolSignals = signals.filter(
        (s) => s.symbol.toUpperCase() === symbol.toUpperCase(),
      )
      addSignalMarkers(cs, symbolSignals)
    } else {
      // Clear markers when toggled off — guard against series being removed during cleanup
      try { cs.setMarkers([]) } catch { /* series may already be disposed */ }
    }
  }, [overlayState.showSignalMarkers, signals, symbol, candles])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <label htmlFor="symbol-select" className="text-[var(--kt-on-surface-variant)] text-sm">
          Symbol
        </label>
        <select
          id="symbol-select"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="bg-[var(--kt-surface-container-high)] border border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] text-sm rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-[var(--kt-primary-container)]"
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
