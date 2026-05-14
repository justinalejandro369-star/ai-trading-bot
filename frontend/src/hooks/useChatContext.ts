/**
 * Hook to build chat context from the active dashboard tab.
 * Reads relevant data from TanStack Query cache per tab.
 */
import { useQueryClient } from '@tanstack/react-query'
import type { ChatContext } from '@/api/chat'
import type { Signal, PaperAccount, BacktestResult } from '@/types'

export function useChatContext(activeTab: string): ChatContext {
  const queryClient = useQueryClient()

  const context: ChatContext = { active_tab: activeTab }

  if (activeTab === 'signals') {
    // Read signals from TanStack Query cache
    const signals = queryClient.getQueryData<Signal[]>(['signals', 'top'])
    if (signals) {
      context.signals = signals.slice(0, 5).map((s) => ({
        symbol: s.symbol,
        direction: s.direction,
        confidence: s.confidence,
        regime: s.regime,
      }))
    }
  }

  if (activeTab === 'portfolio') {
    // Read portfolio from TanStack Query cache
    const account = queryClient.getQueryData<PaperAccount>(['paper', 'account'])
    if (account) {
      context.portfolio = {
        cash_balance: account.cash_balance,
        total_equity: account.total_equity,
        open_positions: account.open_positions.map((p) => ({
          symbol: p.symbol,
          quantity: p.quantity,
          avg_entry_price: p.avg_entry_price,
        })),
      }
    }
  }

  if (activeTab === 'backtest') {
    // Read latest backtest from TanStack Query cache
    const bt = queryClient.getQueryData<BacktestResult>(['backtest'])
    if (bt) {
      context.backtest = {
        sharpe_ratio: bt.sharpe_ratio,
        max_drawdown: bt.max_drawdown,
        win_rate: bt.win_rate,
        profit_factor: bt.profit_factor,
        total_return: bt.total_return,
        total_trades: bt.total_trades,
      }
    }
  }

  return context
}
