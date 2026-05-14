/**
 * Chat API client — sends messages to the contextual chatbot endpoint.
 */
import { apiPost } from './client'

export interface ChatContext {
  active_tab: string
  symbol?: string
  close?: number
  signals?: Array<{
    symbol: string
    direction: string
    confidence: number
    regime: string
  }>
  portfolio?: {
    cash_balance: number
    total_equity: number
    open_positions: Array<{
      symbol: string
      quantity: number
      avg_entry_price: number
    }>
  }
  backtest?: {
    sharpe_ratio: number
    max_drawdown: number
    win_rate: number
    profit_factor: number
    total_return: number
    total_trades: number
  }
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatRequest {
  message: string
  context: ChatContext
  history: ChatHistoryMessage[]
  model?: string | null
}

interface ChatResponse {
  reply: string
}

export async function sendChatMessage(
  message: string,
  context: ChatContext,
  history: ChatHistoryMessage[],
  model?: string | null,
): Promise<string> {
  const body: ChatRequest = { message, context, history }
  if (model) {
    body.model = model
  }
  const response = await apiPost<ChatResponse>('/api/chat/message', body)
  return response.reply
}
