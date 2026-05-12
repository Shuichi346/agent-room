import { useEffect, useRef } from 'react'

import { useAppStore } from '../lib/store'
import MessageBubble from './MessageBubble'

export default function ChatStream() {
  const messages = useAppStore((state) => state.messages)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])

  return (
    <section className="chat-stream">
      <div className="system-pill">Conversation started at {new Date().toLocaleTimeString()}</div>
      {messages.length === 0 ? (
        <div className="empty-chat">
          <h2>Start a room</h2>
          <p>Type a topic, attach context, and let the configured agents debate it.</p>
        </div>
      ) : (
        messages.map((message) => <MessageBubble key={message.id} message={message} />)
      )}
      <div ref={bottomRef} />
    </section>
  )
}

