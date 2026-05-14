import { cn } from '@/lib/utils'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatMessage({ role, content }: ChatMessageProps) {
  const isUser = role === 'user'

  return (
    <div
      data-testid={`chat-message-${role}`}
      className={cn('flex', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-slate-700 text-slate-200',
        )}
      >
        {content}
      </div>
    </div>
  )
}
