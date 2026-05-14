/**
 * Zustand store for chart overlay toggle state.
 *
 * Tracks which indicator overlays and geometric analysis tools are enabled.
 * The UI redesign will wire toggle buttons to these actions — for now they
 * can be toggled via browser console or devtools.
 */
import { create } from 'zustand'

type PivotMethod = 'standard' | 'camarilla' | 'woodie'

/** All boolean toggle keys that can be passed to toggle() */
type ToggleKey =
  | 'showEma50'
  | 'showEma200'
  | 'showBollingerBands'
  | 'showRsi'
  | 'showMacd'
  | 'showVolume'
  | 'showFibonacci'
  | 'showTrendlines'
  | 'showSupportResistance'
  | 'showPivotPoints'
  | 'showSignalMarkers'

interface ChartOverlayState {
  showEma50: boolean
  showEma200: boolean
  showBollingerBands: boolean
  showRsi: boolean
  showMacd: boolean
  showVolume: boolean
  showFibonacci: boolean
  showTrendlines: boolean
  showSupportResistance: boolean
  showPivotPoints: boolean
  pivotMethod: PivotMethod
  showSignalMarkers: boolean
  toggle: (key: ToggleKey) => void
  setPivotMethod: (method: PivotMethod) => void
}

export const useChartOverlayStore = create<ChartOverlayState>((set) => ({
  // All overlays default off — user enables what they want
  showEma50: false,
  showEma200: false,
  showBollingerBands: false,
  showRsi: false,
  showMacd: false,
  showVolume: false,
  showFibonacci: false,
  showTrendlines: false,
  showSupportResistance: false,
  showPivotPoints: false,
  pivotMethod: 'standard',
  showSignalMarkers: false,

  toggle: (key) => set((state) => ({ [key]: !state[key] })),
  setPivotMethod: (method) => set({ pivotMethod: method }),
}))
