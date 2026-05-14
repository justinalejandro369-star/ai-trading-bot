/**
 * Data-fetching hook for chart overlays.
 *
 * Uses TanStack Query to fetch indicator series and chart analysis data,
 * gated by the Zustand overlay toggle state. Only fetches data when at least
 * one overlay in the category is enabled — avoids wasted API calls.
 */
import { useQuery } from '@tanstack/react-query'
import { getIndicatorSeries, getChartAnalysis } from '@/api/market'
import { useChartOverlayStore } from '@/store/chartOverlays'
import type { IndicatorSeries, ChartAnalysis } from '@/types'

interface ChartOverlayData {
  indicatorSeries: IndicatorSeries | undefined
  chartAnalysis: ChartAnalysis | undefined
  isLoading: boolean
}

/**
 * Fetches overlay data for a symbol, gated by toggle state.
 *
 * Indicator series (EMA, BB, RSI, MACD, volume) are fetched when any
 * indicator toggle is on. Chart analysis (Fibonacci, trendlines, S/R, pivots)
 * is fetched when any geometric analysis toggle is on.
 */
export function useChartOverlays(
  symbol: string,
  interval = '1D',
  limit = 200,
): ChartOverlayData {
  const store = useChartOverlayStore()

  // Determine if we need indicator series data (any indicator overlay is on)
  const needIndicators =
    store.showEma50 ||
    store.showEma200 ||
    store.showBollingerBands ||
    store.showRsi ||
    store.showMacd ||
    store.showVolume

  // Determine if we need chart analysis data (any geometric overlay is on)
  const needAnalysis =
    store.showFibonacci ||
    store.showTrendlines ||
    store.showSupportResistance ||
    store.showPivotPoints

  const {
    data: indicatorSeries,
    isLoading: indicatorsLoading,
  } = useQuery<IndicatorSeries>({
    queryKey: ['indicator-series', symbol, interval, limit],
    queryFn: () => getIndicatorSeries(symbol, interval, limit),
    enabled: needIndicators,
    staleTime: 60_000,
  })

  const {
    data: chartAnalysis,
    isLoading: analysisLoading,
  } = useQuery<ChartAnalysis>({
    queryKey: ['chart-analysis', symbol, interval, store.pivotMethod],
    queryFn: () => getChartAnalysis(symbol, interval, store.pivotMethod),
    enabled: needAnalysis,
    staleTime: 60_000,
  })

  return {
    indicatorSeries,
    chartAnalysis,
    isLoading: (needIndicators && indicatorsLoading) || (needAnalysis && analysisLoading),
  }
}
