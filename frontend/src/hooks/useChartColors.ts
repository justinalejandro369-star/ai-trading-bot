import { useThemeStore } from '@/store/theme'

// Returns a consistent color palette for Recharts components based on current theme.
// Kinetic Terminal palette — dark mode uses the MD3 trading terminal colors.
export function useChartColors() {
  const resolved = useThemeStore((s) => s.resolved)

  return resolved === 'dark'
    ? {
        grid: '#1D2023',
        text: '#C3C6D7',
        tooltipBg: '#191C1F',
        tooltipBorder: '#424654',
        green: '#44E092',
        blue: '#5D8BFF',
        red: '#FF5451',
        legendText: '#C3C6D7',
      }
    : {
        grid: '#e2e8f0',
        text: '#64748b',
        tooltipBg: '#ffffff',
        tooltipBorder: '#e2e8f0',
        green: '#059669',
        blue: '#2563eb',
        red: '#dc2626',
        legendText: '#64748b',
      }
}
