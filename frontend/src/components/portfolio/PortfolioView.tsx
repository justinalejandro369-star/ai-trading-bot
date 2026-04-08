import { useQuery } from '@tanstack/react-query'
import { getAccount, getEquityCurve } from '@/api/paper'
import { Card, CardContent } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import EquityCurveChart from '@/components/chart/EquityCurveChart'
import PnLPieChart from '@/components/chart/PnLPieChart'
import type { PaperAccount, EquityPoint } from '@/types'

const ACCOUNT_ID = 1

function colorPnl(val: number) {
  return val >= 0 ? 'text-emerald-400' : 'text-red-400'
}

export default function PortfolioView() {
  const { data: account, isLoading: loadingAccount } = useQuery<PaperAccount>({
    queryKey: ['account', ACCOUNT_ID],
    queryFn: () => getAccount(ACCOUNT_ID),
    staleTime: 30_000,
    refetchInterval: 60_000,
  })

  const { data: equityCurve = [] } = useQuery<EquityPoint[]>({
    queryKey: ['equity', ACCOUNT_ID],
    queryFn: () => getEquityCurve(ACCOUNT_ID),
    staleTime: 30_000,
  })

  if (loadingAccount) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
        Loading portfolio...
      </div>
    )
  }

  if (!account) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-400 text-sm">
        Portfolio unavailable
      </div>
    )
  }

  const pnl = account.balance - account.initial_balance
  const returnPct = ((pnl / account.initial_balance) * 100).toFixed(2)

  return (
    <div data-testid="portfolio-view" className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="pt-4">
            <div className="text-xs text-slate-500 mb-1">Balance</div>
            <div className="text-xl font-bold text-slate-100">
              ${account.balance.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="pt-4">
            <div className="text-xs text-slate-500 mb-1">P&amp;L</div>
            <div className={`text-xl font-bold ${colorPnl(pnl)}`}>
              {pnl >= 0 ? '+' : ''}${pnl.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-800 border-slate-700">
          <CardContent className="pt-4">
            <div className="text-xs text-slate-500 mb-1">Return</div>
            <div className={`text-xl font-bold ${colorPnl(pnl)}`}>
              {pnl >= 0 ? '+' : ''}{returnPct}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Positions table */}
      <div>
        <h3 className="text-sm font-semibold text-slate-300 mb-2">Open Positions</h3>
        {account.positions.length === 0 ? (
          <div className="flex items-center justify-center h-20 bg-slate-800 rounded-lg border border-slate-700">
            <p className="text-slate-500 text-sm">No open positions</p>
          </div>
        ) : (
          <div className="rounded-lg border border-slate-700 overflow-hidden">
            <Table data-testid="positions-table">
              <TableHeader>
                <TableRow className="border-slate-700 hover:bg-transparent">
                  <TableHead className="text-slate-400">Symbol</TableHead>
                  <TableHead className="text-slate-400">Qty</TableHead>
                  <TableHead className="text-slate-400">Avg Price</TableHead>
                  <TableHead className="text-slate-400">Current</TableHead>
                  <TableHead className="text-slate-400">P&amp;L</TableHead>
                  <TableHead className="text-slate-400">%</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {account.positions.map((pos) => {
                  const posPct = ((pos.pnl / (pos.avg_price * pos.quantity)) * 100).toFixed(2)
                  return (
                    <TableRow key={pos.symbol} className="border-slate-700">
                      <TableCell className="text-slate-100 font-medium">{pos.symbol}</TableCell>
                      <TableCell className="text-slate-300">{pos.quantity}</TableCell>
                      <TableCell className="text-slate-300">${pos.avg_price.toFixed(2)}</TableCell>
                      <TableCell className="text-slate-300">${pos.current_price.toFixed(2)}</TableCell>
                      <TableCell className={colorPnl(pos.pnl)}>
                        {pos.pnl >= 0 ? '+' : ''}${pos.pnl.toFixed(2)}
                      </TableCell>
                      <TableCell className={colorPnl(pos.pnl)}>
                        {pos.pnl >= 0 ? '+' : ''}{posPct}%
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Equity Curve</h3>
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-3">
            <EquityCurveChart data={equityCurve} />
          </div>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Allocation</h3>
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-3">
            <PnLPieChart positions={account.positions} />
          </div>
        </div>
      </div>
    </div>
  )
}
