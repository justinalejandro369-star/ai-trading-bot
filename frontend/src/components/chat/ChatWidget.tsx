import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import ChatMessage from './ChatMessage'
import { sendChatMessage, type ChatHistoryMessage } from '@/api/chat'
import { useChatContext } from '@/hooks/useChatContext'

/** Available free models on OpenRouter */
const FREE_MODELS = [
  { id: 'meta-llama/llama-4-scout:free', label: 'Llama 4 Scout' },
  { id: 'deepseek/deepseek-r1:free', label: 'DeepSeek R1' },
  { id: 'qwen/qwen3-235b-a22b:free', label: 'Qwen3 235B' },
]

interface ChatWidgetProps {
  activeTab: string
}

export default function ChatWidget({ activeTab }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatHistoryMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState(FREE_MODELS[0].id)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const chatContext = useChatContext(activeTab)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    const userMsg: ChatHistoryMessage = { role: 'user', content: trimmed }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      // Send last 5 exchanges (10 messages) for context continuity
      const history = [...messages, userMsg].slice(-10)
      const reply = await sendChatMessage(trimmed, chatContext, history, selectedModel)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, messages, chatContext, selectedModel])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <>
      {/* Floating toggle button */}
      <button
        data-testid="chat-toggle"
        onClick={() => setIsOpen((prev) => !prev)}
        className="fixed bottom-6 right-6 z-50 h-12 w-12 rounded-full bg-[var(--kt-primary-container)] text-white shadow-lg hover:opacity-90 flex items-center justify-center transition-all"
        aria-label={isOpen ? 'Close chat' : 'Open chat'}
      >
        {isOpen ? (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
          </svg>
        )}
      </button>

      {/* Chat panel — glassmorphism */}
      {isOpen && (
        <div
          data-testid="chat-panel"
          className="fixed bottom-20 right-6 z-50 w-96 max-h-[500px] flex flex-col rounded-xl border border-[rgba(66,70,84,0.15)] bg-[rgba(50,53,56,0.6)] backdrop-blur-[24px] shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[rgba(66,70,84,0.15)] px-4 py-3">
            <span className="text-sm font-semibold text-[var(--kt-on-surface)]">Trading Assistant</span>
            {/* Model selector */}
            <select
              data-testid="chat-model-selector"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="text-xs bg-[var(--kt-surface-container-high)] text-[var(--kt-on-surface-variant)] border border-[rgba(66,70,84,0.15)] rounded px-2 py-1 outline-none"
            >
              {FREE_MODELS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-[200px] max-h-[340px]">
            {messages.length === 0 && (
              <div className="text-xs text-[var(--kt-on-surface-variant)] text-center mt-8">
                Ask me anything about trading, signals, or your portfolio.
              </div>
            )}
            {messages.map((msg, i) => (
              <ChatMessage key={i} role={msg.role} content={msg.content} />
            ))}
            {isLoading && (
              <div data-testid="chat-loading" className="flex justify-start">
                <div className="bg-[var(--kt-surface-container-high)] text-[var(--kt-on-surface-variant)] rounded-lg px-3 py-2 text-sm">
                  <span className="animate-pulse">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="border-t border-[rgba(66,70,84,0.15)] p-3">
            <div className="flex gap-2">
              <Textarea
                ref={textareaRef}
                data-testid="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about signals, indicators, strategies..."
                className="min-h-[40px] max-h-[80px] resize-none bg-[var(--kt-surface-container-lowest)] border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] text-sm placeholder:text-[var(--kt-on-surface-variant)]"
                rows={1}
              />
              <Button
                data-testid="chat-send"
                size="icon"
                onClick={() => void handleSend()}
                disabled={!input.trim() || isLoading}
                className="shrink-0 bg-[var(--kt-primary-container)] hover:opacity-90"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                </svg>
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
