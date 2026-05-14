import { Button } from '@/components/ui/button'
import { useThemeStore } from '@/store/theme'

interface TopBarProps {
  username?: string | null
  onLogout: () => void
}

// Sun icon for light mode indicator
function SunIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  )
}

// Moon icon for dark mode indicator
function MoonIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

// Monitor icon for system mode indicator
function MonitorIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  )
}

/* Ticker nav items — S&P 500 is active (green), rest are muted */
const TICKERS = [
  { label: 'S&P 500', active: true },
  { label: 'BTC/USDT', active: false },
  { label: 'ETH/USDT', active: false },
  { label: 'EUR/USD', active: false },
]

export default function TopBar({ username, onLogout }: TopBarProps) {
  const { theme, setTheme } = useThemeStore()

  const cycleTheme = () => {
    const next = theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'
    setTheme(next)
  }

  return (
    <header
      data-testid="dashboard-nav"
      className="h-14 shrink-0 flex items-center justify-between px-6 bg-[#111417]/80 backdrop-blur-xl border-b border-[#424654]/15 font-['Inter'] text-[0.75rem] uppercase tracking-widest"
    >
      {/* Left: Search bar */}
      <div className="flex items-center gap-6">
        {/* Search input styled to match Stitch surface-container-lowest */}
        <div className="hidden md:flex items-center gap-2 bg-[#0B0E11] px-3 py-1.5 rounded-lg border border-[#424654]/10">
          <span className="material-symbols-outlined text-[#C3C6D7]" style={{ fontSize: 16 }}>
            search
          </span>
          <input
            type="text"
            placeholder="SEARCH ASSETS..."
            className="bg-transparent border-none outline-none text-[0.75rem] uppercase tracking-widest text-[#C3C6D7] placeholder:text-[#C3C6D7]/50 w-32 font-['Inter']"
          />
        </div>

        {/* Center: Ticker navigation links */}
        <div className="hidden md:flex items-center gap-4">
          {TICKERS.map((ticker) => (
            <span
              key={ticker.label}
              className={
                ticker.active
                  ? 'text-[#44E092] font-bold cursor-pointer transition-colors'
                  : 'text-[#C3C6D7] hover:text-[#E1E2E7] cursor-pointer transition-colors'
              }
            >
              {ticker.label}
            </span>
          ))}
        </div>
      </div>

      {/* Mobile: Brand name (visible when sidebar is hidden) */}
      <div className="md:hidden font-bold text-lg normal-case tracking-normal text-[#E1E2E7] font-[var(--heading)]">
        Kinetic Terminal
      </div>

      {/* Right: Icons, user info, theme toggle, logout */}
      <div className="flex items-center gap-4">
        {/* Notifications icon */}
        <span className="material-symbols-outlined text-[#C3C6D7] hover:text-[#E1E2E7] cursor-pointer transition-colors" style={{ fontSize: 20 }}>
          notifications
        </span>

        {/* Person / account icon */}
        <span className="material-symbols-outlined text-[#C3C6D7] hover:text-[#E1E2E7] cursor-pointer transition-colors" style={{ fontSize: 20 }}>
          person
        </span>

        {/* Separator */}
        <div className="border-l border-[#424654]/20 h-6" />

        {/* User info block */}
        <div className="hidden sm:flex flex-col items-end leading-tight">
          <span className="text-[0.6rem] text-[#44E092] font-bold tracking-widest">CONNECTED</span>
          <span className="text-[0.65rem] text-[#C3C6D7] tracking-wider normal-case">
            {username || 'AI TRADER ADMIN'}
          </span>
        </div>

        {/* Theme toggle — styled to match Stitch aesthetic */}
        <Button
          variant="ghost"
          size="sm"
          onClick={cycleTheme}
          className="text-[#C3C6D7] hover:bg-[#272A2E] hover:text-[#E1E2E7] p-1.5 h-auto"
          title={`Theme: ${theme}`}
        >
          {theme === 'light' ? <SunIcon /> : theme === 'dark' ? <MoonIcon /> : <MonitorIcon />}
        </Button>

        {/* Logout button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onLogout}
          className="text-[#C3C6D7] hover:bg-[#272A2E] hover:text-[#E1E2E7] text-[0.7rem] uppercase tracking-widest h-auto px-2 py-1"
        >
          Logout
        </Button>
      </div>
    </header>
  )
}
