import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send } from 'lucide-react'
import { ChatMsg } from '../../types'
import clsx from 'clsx'

interface ChatPanelProps {
  messages: ChatMsg[]
  onSend: (msg: string) => void
  disabled?: boolean
}

export default function ChatPanel({ messages, onSend, disabled = false }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  const handleSend = () => {
    const msg = input.trim()
    if (!msg || disabled) return
    onSend(msg)
    setInput('')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {messages.length === 0 && (
          <p className="text-nebula-500 text-xs text-center pt-4">Say hello! 👋</p>
        )}
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={clsx(
                'text-sm',
                msg.system ? 'text-nebula-400 italic text-center text-xs' : ''
              )}
            >
              {!msg.system && (
                <>
                  <span className="font-semibold text-nebula-300">{msg.username}: </span>
                  <span className="text-nebula-100">{msg.message}</span>
                </>
              )}
              {msg.system && <span>{msg.message}</span>}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-nebula-700/40">
        <div className="flex gap-2">
          <input
            className="input flex-1 py-2 text-xs"
            placeholder={disabled ? 'Log in to chat' : 'Type a message…'}
            value={input}
            disabled={disabled}
            onChange={e => setInput(e.target.value.slice(0, 280))}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || disabled}
            className="btn-primary py-2 px-3 rounded-lg disabled:opacity-40"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
