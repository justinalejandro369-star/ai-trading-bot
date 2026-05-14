import { create } from 'zustand'

type Theme = 'light' | 'dark' | 'system'
type Resolved = 'light' | 'dark'

interface ThemeStore {
  theme: Theme
  resolved: Resolved
  setTheme: (t: Theme) => void
}

// Resolve 'system' preference to actual light/dark value
function resolveTheme(theme: Theme): Resolved {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}

// Apply or remove the .dark class on <html>
function applyTheme(resolved: Resolved) {
  if (resolved === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// Read persisted preference from localStorage
const stored = (typeof window !== 'undefined' ? localStorage.getItem('theme') : null) as Theme | null
const initialTheme: Theme = stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'dark'
const initialResolved = resolveTheme(initialTheme)

// Apply theme immediately to avoid flash of wrong theme
applyTheme(initialResolved)

export const useThemeStore = create<ThemeStore>((set) => ({
  theme: initialTheme,
  resolved: initialResolved,

  setTheme: (t: Theme) => {
    const resolved = resolveTheme(t)
    applyTheme(resolved)
    localStorage.setItem('theme', t)
    set({ theme: t, resolved })
  },
}))

// Listen for OS-level color scheme changes when in 'system' mode
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const state = useThemeStore.getState()
    if (state.theme === 'system') {
      const resolved = resolveTheme('system')
      applyTheme(resolved)
      useThemeStore.setState({ resolved })
    }
  })
}
