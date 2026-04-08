import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { logoutUser } from '@/api/auth'
import { useAuthStore } from '@/store/auth'

export default function Dashboard() {
  const navigate = useNavigate()
  const { isAuthenticated, username, checkAuth, clearAuth } = useAuthStore()

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
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Top nav */}
      <header data-testid="dashboard-nav" className="border-b border-slate-700 bg-slate-800 px-6 py-3 flex items-center justify-between">
        <div className="font-bold text-lg text-blue-400">Trading Bot</div>
        <div className="flex items-center gap-4">
          {username && (
            <span className="text-slate-400 text-sm">{username}</span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => void handleLogout()}
            className="border-slate-600 text-slate-300 hover:bg-slate-700"
          >
            Logout
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 p-6">
        <Tabs defaultValue="chart" data-testid="dashboard-tabs" className="w-full">
          <TabsList className="bg-slate-800 border-slate-700 mb-6">
            <TabsTrigger value="chart" className="data-[state=active]:bg-slate-700">
              Chart
            </TabsTrigger>
            <TabsTrigger value="signals" className="data-[state=active]:bg-slate-700">
              Signals
            </TabsTrigger>
            <TabsTrigger value="portfolio" className="data-[state=active]:bg-slate-700">
              Portfolio
            </TabsTrigger>
            <TabsTrigger value="backtest" className="data-[state=active]:bg-slate-700">
              Backtest
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chart">
            <div className="flex items-center justify-center h-64 bg-slate-800 rounded-lg border border-slate-700">
              <p className="text-slate-400">Candlestick Chart — Coming in Wave 3</p>
            </div>
          </TabsContent>

          <TabsContent value="signals">
            <div className="flex items-center justify-center h-64 bg-slate-800 rounded-lg border border-slate-700">
              <p className="text-slate-400">Signal Feed — Coming in Wave 3</p>
            </div>
          </TabsContent>

          <TabsContent value="portfolio">
            <div className="flex items-center justify-center h-64 bg-slate-800 rounded-lg border border-slate-700">
              <p className="text-slate-400">Portfolio View — Coming in Wave 3</p>
            </div>
          </TabsContent>

          <TabsContent value="backtest">
            <div className="flex items-center justify-center h-64 bg-slate-800 rounded-lg border border-slate-700">
              <p className="text-slate-400">Backtest Results — Coming in Wave 3</p>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
