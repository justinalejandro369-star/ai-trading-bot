/**
 * Chart overlay series manager.
 *
 * Utility functions that take an IChartApi reference and indicator/analysis data,
 * add TradingView Lightweight Charts series for each overlay type, and return
 * cleanup handles. Each function is self-contained — the CandlestickChart component
 * calls them based on toggle state and removes series when toggled off.
 *
 * All functions follow the v5 API: chart.addSeries(SeriesType, options, paneIndex?)
 */
import {
  LineSeries,
  HistogramSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type SeriesType,
  type Time,
} from 'lightweight-charts'
import type {
  IndicatorSeries,
  ChartAnalysis,
  Signal,
} from '@/types'

// ---------- Helpers ----------

/** Convert ISO timestamp to Unix seconds for TradingView Time type */
function toTime(iso: string): Time {
  return Math.floor(new Date(iso).getTime() / 1000) as unknown as Time
}

/**
 * Build line data from parallel timestamp + value arrays, skipping nulls.
 * Both arrays come from IndicatorSeries and are aligned 1:1.
 */
function buildLineData(
  timestamps: string[],
  values: (number | null)[],
): { time: Time; value: number }[] {
  const data: { time: Time; value: number }[] = []
  for (let i = 0; i < timestamps.length; i++) {
    if (values[i] != null) {
      data.push({ time: toTime(timestamps[i]), value: values[i]! })
    }
  }
  return data
}

// ---------- EMA Overlays (Main Pane) ----------

export function addEmaSeries(
  chart: IChartApi,
  data: IndicatorSeries,
): ISeriesApi<SeriesType>[] {
  const series: ISeriesApi<SeriesType>[] = []

  // EMA 50 — blue line
  if (data.ema_50.some((v) => v != null)) {
    const ema50 = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 1,
      title: 'EMA 50',
    })
    ema50.setData(buildLineData(data.timestamps, data.ema_50))
    series.push(ema50)
  }

  // EMA 200 — orange line
  if (data.ema_200.some((v) => v != null)) {
    const ema200 = chart.addSeries(LineSeries, {
      color: '#f97316',
      lineWidth: 1,
      title: 'EMA 200',
    })
    ema200.setData(buildLineData(data.timestamps, data.ema_200))
    series.push(ema200)
  }

  return series
}

// ---------- Bollinger Bands (Main Pane) ----------

export function addBollingerBands(
  chart: IChartApi,
  data: IndicatorSeries,
): ISeriesApi<SeriesType>[] {
  const series: ISeriesApi<SeriesType>[] = []

  // Upper band — dashed gray
  if (data.bb_upper.some((v) => v != null)) {
    const upper = chart.addSeries(LineSeries, {
      color: '#64748b',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'BB Upper',
    })
    upper.setData(buildLineData(data.timestamps, data.bb_upper))
    series.push(upper)
  }

  // Mid band (SMA 20) — dotted gray
  if (data.bb_mid.some((v) => v != null)) {
    const mid = chart.addSeries(LineSeries, {
      color: '#94a3b8',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      title: 'BB Mid',
    })
    mid.setData(buildLineData(data.timestamps, data.bb_mid))
    series.push(mid)
  }

  // Lower band — dashed gray
  if (data.bb_lower.some((v) => v != null)) {
    const lower = chart.addSeries(LineSeries, {
      color: '#64748b',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: 'BB Lower',
    })
    lower.setData(buildLineData(data.timestamps, data.bb_lower))
    series.push(lower)
  }

  return series
}

// ---------- RSI Sub-Pane (Pane 1) ----------

export function addRsiPane(
  chart: IChartApi,
  data: IndicatorSeries,
): ISeriesApi<SeriesType>[] {
  const series: ISeriesApi<SeriesType>[] = []

  if (!data.rsi_14.some((v) => v != null)) return series

  const rsi = chart.addSeries(LineSeries, {
    color: '#f59e0b',
    lineWidth: 1,
    title: 'RSI 14',
  }, 1)

  rsi.setData(buildLineData(data.timestamps, data.rsi_14))

  // Overbought/oversold horizontal reference lines
  rsi.createPriceLine({ price: 70, color: '#ef4444', lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: false, title: '' })
  rsi.createPriceLine({ price: 30, color: '#10b981', lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: false, title: '' })

  series.push(rsi)
  return series
}

// ---------- MACD Sub-Pane (Pane 2) ----------

export function addMacdPane(
  chart: IChartApi,
  data: IndicatorSeries,
): ISeriesApi<SeriesType>[] {
  const series: ISeriesApi<SeriesType>[] = []

  // MACD line — blue
  if (data.macd_val.some((v) => v != null)) {
    const macdLine = chart.addSeries(LineSeries, {
      color: '#3b82f6',
      lineWidth: 1,
      title: 'MACD',
    }, 2)
    macdLine.setData(buildLineData(data.timestamps, data.macd_val))
    series.push(macdLine)
  }

  // Signal line — orange
  if (data.macd_signal.some((v) => v != null)) {
    const signalLine = chart.addSeries(LineSeries, {
      color: '#f97316',
      lineWidth: 1,
      title: 'Signal',
    }, 2)
    signalLine.setData(buildLineData(data.timestamps, data.macd_signal))
    series.push(signalLine)
  }

  // Histogram — green/red bars
  if (data.macd_hist.some((v) => v != null)) {
    const hist = chart.addSeries(HistogramSeries, {
      title: 'Hist',
    }, 2)
    const histData = data.timestamps
      .map((ts, i) => {
        const val = data.macd_hist[i]
        if (val == null) return null
        return {
          time: toTime(ts),
          value: val,
          color: val >= 0 ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)',
        }
      })
      .filter((d): d is NonNullable<typeof d> => d !== null)
    hist.setData(histData)
    series.push(hist)
  }

  return series
}

// ---------- Volume (Main Pane, Low Opacity) ----------

export function addVolumeSeries(
  chart: IChartApi,
  data: IndicatorSeries,
): ISeriesApi<SeriesType>[] {
  const series: ISeriesApi<SeriesType>[] = []

  // Volume bars — low opacity so they don't obscure candlesticks
  const vol = chart.addSeries(HistogramSeries, {
    color: 'rgba(100, 116, 139, 0.3)',
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
    title: 'Vol',
  })

  // Configure volume price scale to occupy bottom 20% of the pane
  chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
  })

  const volData = data.timestamps.map((ts, i) => ({
    time: toTime(ts),
    value: data.volume[i],
  }))
  vol.setData(volData)
  series.push(vol)

  // Volume SMA 20 overlay
  if (data.vol_sma_20.some((v) => v != null)) {
    const volSma = chart.addSeries(LineSeries, {
      color: '#a78bfa',
      lineWidth: 1,
      priceScaleId: 'volume',
      title: 'Vol SMA',
    })
    volSma.setData(buildLineData(data.timestamps, data.vol_sma_20))
    series.push(volSma)
  }

  return series
}

// ---------- Fibonacci Levels (PriceLines on main pane) ----------

/** Fibonacci levels are added as PriceLines on the candlestick series. */
export function addFibonacciLevels(
  candleSeries: ISeriesApi<SeriesType>,
  analysis: ChartAnalysis,
): void {
  if (!analysis.fibonacci) return

  const { retracement } = analysis.fibonacci

  // Fibonacci color palette — golden tones
  const colors: Record<string, string> = {
    '0.0': '#10b981',   // green - swing extreme
    '0.236': '#34d399',
    '0.382': '#fbbf24',
    '0.5': '#f59e0b',
    '0.618': '#f97316',  // golden ratio — most important
    '0.786': '#ef4444',
    '1.0': '#dc2626',   // red - opposite swing extreme
  }

  for (const [level, price] of Object.entries(retracement)) {
    candleSeries.createPriceLine({
      price,
      color: colors[level] || '#94a3b8',
      lineWidth: 1,
      lineStyle: level === '0.618' ? LineStyle.Solid : LineStyle.Dotted,
      axisLabelVisible: true,
      title: `Fib ${level}`,
    })
  }
}

// ---------- Trend Lines (LineSeries with 2 data points each) ----------

export function addTrendLines(
  chart: IChartApi,
  analysis: ChartAnalysis,
): ISeriesApi<SeriesType>[] {
  const series: ISeriesApi<SeriesType>[] = []

  for (const line of analysis.trendlines.lines) {
    const color = line.direction === 'ascending' ? '#10b981' : '#ef4444'
    const s = chart.addSeries(LineSeries, {
      color,
      lineWidth: 2,
      lineStyle: LineStyle.LargeDashed,
      // No title to avoid cluttering the legend
      lastValueVisible: false,
      priceLineVisible: false,
    })
    s.setData([
      { time: toTime(line.start_time), value: line.start_price },
      { time: toTime(line.end_time), value: line.end_price },
    ])
    series.push(s)
  }

  return series
}

// ---------- Support/Resistance Levels (PriceLines) ----------

export function addSRLevels(
  candleSeries: ISeriesApi<SeriesType>,
  analysis: ChartAnalysis,
): void {
  for (const level of analysis.support_resistance.levels) {
    const color =
      level.level_type === 'support'
        ? '#10b981'
        : level.level_type === 'resistance'
          ? '#ef4444'
          : '#f59e0b' // "both"

    candleSeries.createPriceLine({
      price: level.price,
      color,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: `${level.level_type[0].toUpperCase()}${level.level_type.slice(1)} (${level.touches})`,
    })
  }
}

// ---------- Pivot Points (PriceLines) ----------

export function addPivotPoints(
  candleSeries: ISeriesApi<SeriesType>,
  analysis: ChartAnalysis,
): void {
  if (!analysis.pivots) return

  const { pivots } = analysis

  // Pivot — blue
  candleSeries.createPriceLine({
    price: pivots.pivot,
    color: '#3b82f6',
    lineWidth: 1,
    lineStyle: LineStyle.Solid,
    axisLabelVisible: true,
    title: 'P',
  })

  // Resistance levels — red (lighter for R1, darker for R3)
  const rColors = ['#f87171', '#ef4444', '#dc2626']
  const rValues = [pivots.r1, pivots.r2, pivots.r3]
  rValues.forEach((price, i) => {
    candleSeries.createPriceLine({
      price,
      color: rColors[i],
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: `R${i + 1}`,
    })
  })

  // Support levels — green (lighter for S1, darker for S3)
  const sColors = ['#34d399', '#10b981', '#059669']
  const sValues = [pivots.s1, pivots.s2, pivots.s3]
  sValues.forEach((price, i) => {
    candleSeries.createPriceLine({
      price,
      color: sColors[i],
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: `S${i + 1}`,
    })
  })
}

// ---------- Signal Markers (BUY/SELL arrows on candle series) ----------

export function addSignalMarkers(
  candleSeries: ISeriesApi<SeriesType>,
  signals: Signal[],
): void {
  if (!signals.length) return

  const markers = signals
    .filter((s) => s.direction !== 'HOLD')
    .map((s) => ({
      time: Math.floor(new Date(s.scanned_at).getTime() / 1000) as unknown as Time,
      position: s.direction === 'BUY' ? 'belowBar' as const : 'aboveBar' as const,
      color: s.direction === 'BUY' ? '#10b981' : '#ef4444',
      shape: s.direction === 'BUY' ? 'arrowUp' as const : 'arrowDown' as const,
      text: `${s.direction} ${s.confidence}%`,
    }))
    // TradingView requires markers sorted by time ascending
    .sort((a, b) => (a.time as number) - (b.time as number))

  candleSeries.setMarkers(markers)

  // Add entry/stop-loss/target price lines for the most recent signal
  const latest = signals.find((s) => s.direction !== 'HOLD')
  if (!latest) return

  if (latest.entry_price != null) {
    candleSeries.createPriceLine({
      price: latest.entry_price,
      color: '#3b82f6',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Entry',
    })
  }
  if (latest.stop_loss != null) {
    candleSeries.createPriceLine({
      price: latest.stop_loss,
      color: '#ef4444',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'SL',
    })
  }
  if (latest.target_price != null) {
    candleSeries.createPriceLine({
      price: latest.target_price,
      color: '#10b981',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'TP',
    })
  }
}
