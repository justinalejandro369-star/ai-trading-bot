import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { logoutUser } from '@/api/auth'
import { useAuthStore } from '@/store/auth'
import { useWebSocket } from '@/hooks/useWebSocket'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'
import StatusFooter from '@/components/layout/StatusFooter'
import CandlestickChart from '@/components/chart/CandlestickChart'
import SignalFeed from '@/components/signals/SignalFeed'
import PortfolioView from '@/components/portfolio/PortfolioView'
import BacktestResults from '@/components/backtest/BacktestResults'
import PerformanceAudit from '@/components/backtest/PerformanceAudit'
import Education from '@/pages/Education'
import ChatWidget from '@/components/chat/ChatWidget'
import { Button } from '@/components/ui/button'

const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined) ?? 'ws://localhost:8000'

export default function Dashboard() {
  const navigate = useNavigate()
  const { isAuthenticated, username, checkAuth, clearAuth } = useAuthStore()
  // Track active sidebar section for content switching and contextual chat
  const [activeSection, setActiveSection] = useState('dashboard')
  // Toggle between backtest runner and performance audit views
  const [showAudit, setShowAudit] = useState(false)

  useWebSocket(`${WS_URL}/ws/live`)

  useEffect(() => {
    if (!isAuthenticated) {
      void checkAuth()
    }
  }, [isAuthenticated, checkAuth])

  const handleLogout = async () => {
    await logoutUser()
    clearAuth()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#111417]">
      {/* Sidebar navigation */}
      <Sidebar activeSection={activeSection} onSectionChange={setActiveSection} />

      {/* Main content area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <TopBar username={username} onLogout={() => void handleLogout()} />

        <main className="flex-1 overflow-y-auto p-6 pt-4">
          {/* Dashboard: Candlestick chart view */}
          {activeSection === 'dashboard' && <CandlestickChart />}

          {/* Market Scanner: Signal feed */}
          {activeSection === 'scanner' && <SignalFeed />}

          {/* Portfolio: Paper trading view */}
          {activeSection === 'portfolio' && <PortfolioView />}

          {/* Backtesting: Run Backtest + Performance Audit */}
          {activeSection === 'backtesting' && (
            <>
              <div className="flex items-center gap-2 mb-4">
                <Button
                  variant={showAudit ? 'ghost' : 'default'}
                  size="sm"
                  onClick={() => setShowAudit(false)}
                  className={showAudit ? 'text-[var(--kt-on-surface-variant)]' : ''}
                >
                  Run Backtest
                </Button>
                <Button
                  variant={showAudit ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setShowAudit(true)}
                  className={!showAudit ? 'text-[var(--kt-on-surface-variant)]' : ''}
                >
                  Performance Audit
                </Button>
              </div>
              {showAudit ? <PerformanceAudit /> : <BacktestResults />}
            </>
          )}

          {/* Learn: Education glossary */}
          {activeSection === 'learn' && <Education />}
        </main>

        <StatusFooter />
      </div>

      {/* Floating chat widget — contextual AI assistant */}
      <ChatWidget activeTab={activeSection} />
    </div>
  )
}
