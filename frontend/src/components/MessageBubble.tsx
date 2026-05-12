import type { CSSProperties } from 'react'

import type { Message } from '../lib/types'

interface Props {
  message: Message
}

const fallbackColor = '#08D9C7'

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const color = isUser ? '#0FA89A' : isSystem ? '#81909A' : fallbackColor
  const created = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  return (
    <article className={`message-bubble ${isUser ? 'user-message' : ''}`} style={{ '--message-color': color } as CSSProperties}>
      <div className="message-meta">
        <span className="mini-avatar">{message.name.slice(0, 1)}</span>
        <strong>{message.name}</strong>
        <time>{created}</time>
      </div>
      <div className="message-body">
        {message.content.split('\n').map((line, index) => (
          <p key={`${message.id}-${index}`}>{line || '\u00a0'}</p>
        ))}
        {message.attachments.length > 0 && (
          <div className="attachment-list">
            {message.attachments.map((attachment, index) => (
              <span key={`${attachment.kind}-${index}`}>{attachment.kind}: {attachment.source}</span>
            ))}
          </div>
        )}
      </div>
    </article>
  )
}
