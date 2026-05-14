import { cn } from '@/lib/utils'

interface NavItem {
  id: string
  label: string
  icon: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'scanner', label: 'Market Scanner', icon: 'analytics' },
  { id: 'portfolio', label: 'Portfolio', icon: 'account_balance_wallet' },
  { id: 'backtesting', label: 'Backtesting', icon: 'history' },
  { id: 'learn', label: 'Learn', icon: 'school' },
]

interface SidebarProps {
  activeSection: string
  onSectionChange: (section: string) => void
}

export default function Sidebar({ activeSection, onSectionChange }: SidebarProps) {
  return (
    <aside
      data-testid="sidebar-nav"
      className="hidden md:flex flex-col w-64 shrink-0 bg-[#191C1F] h-screen overflow-y-auto py-6 font-['Manrope']"
    >
      {/* Brand area — bolt icon badge + brand name */}
      <div className="px-6 mb-8">
        <div className="flex items-center gap-2">
          {/* Small 8x8-ish rounded bolt icon badge */}
          <div className="w-8 h-8 rounded-lg bg-[#3773F5] flex items-center justify-center">
            <span className="material-symbols-outlined text-white" style={{ fontSize: 16 }}>
              bolt
            </span>
          </div>
          <h1 className="text-xl font-bold text-[#E1E2E7] tracking-tighter">
            Kinetic Terminal
          </h1>
        </div>
        <div className="flex items-center gap-1.5 mt-1.5 pl-10">
          <span className="w-1.5 h-1.5 rounded-full bg-[#44E092]" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#44E092]">
            AI Engine Active
          </span>
        </div>
      </div>

      {/* Navigation — space-y-1 between items, no horizontal padding on nav (items handle their own) */}
      <nav className="flex-1 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = activeSection === item.id
          return (
            <button
              key={item.id}
              onClick={() => onSectionChange(item.id)}
              className={cn(
                'w-full flex items-center gap-3 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-[#323538] rounded-r-lg border-l-4 border-[#3773F5] px-6 py-3 text-[#E1E2E7]'
                  : 'px-6 py-3 text-[#C3C6D7] hover:text-[#E1E2E7] hover:bg-[#323538]',
              )}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
                {item.icon}
              </span>
              {item.label}
            </button>
          )
        })}

        {/* Settings item at the bottom of the nav list, separated by auto-margin */}
        <div className="!mt-auto pt-4">
          <button
            onClick={() => onSectionChange('settings')}
            className={cn(
              'w-full flex items-center gap-3 text-sm font-medium transition-colors',
              activeSection === 'settings'
                ? 'bg-[#323538] rounded-r-lg border-l-4 border-[#3773F5] px-6 py-3 text-[#E1E2E7]'
                : 'px-6 py-3 text-[#C3C6D7] hover:text-[#E1E2E7] hover:bg-[#323538]',
            )}
          >
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
              settings
            </span>
            Settings
          </button>
        </div>
      </nav>

      {/* User profile section at very bottom */}
      <div className="px-6 pt-6 mt-auto">
        <div className="flex items-center gap-3">
          {/* Avatar placeholder */}
          <div className="w-9 h-9 rounded-full bg-[#323538] flex items-center justify-center">
            <span className="material-symbols-outlined text-[#C3C6D7]" style={{ fontSize: 18 }}>
              person
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-[#E1E2E7] truncate">Admin_01</div>
            <div className="text-xs text-[#C3C6D7]">Pro Account</div>
          </div>
        </div>
        {/* Storage bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-[10px] text-[#C3C6D7] mb-1">
            <span>Storage</span>
            <span>75%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-[#323538]">
            <div className="h-1.5 rounded-full bg-[#3773F5]" style={{ width: '75%' }} />
          </div>
        </div>
      </div>
    </aside>
  )
}
