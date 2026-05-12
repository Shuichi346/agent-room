import { Bot, BookOpen, MessageSquare, Plus, Settings2, TerminalSquare } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

import { useAppStore } from '../lib/store'

export default function Sidebar() {
  const navigate = useNavigate()
  const clearConversation = useAppStore((state) => state.clearConversation)
  const conversations = useAppStore((state) => state.conversations)
  const loadConversations = useAppStore((state) => state.loadConversations)
  const loadConversation = useAppStore((state) => state.loadConversation)

  useEffect(() => {
    void loadConversations()
  }, [loadConversations])

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-orb">
          <Bot size={26} />
        </div>
        <div>
          <h1>agent-room</h1>
          <p>Multi-Agent v0.1</p>
        </div>
      </div>

      <button
        className="new-session"
        onClick={() => {
          clearConversation()
          navigate('/simulation')
        }}
      >
        <Plus size={21} />
        New Session
      </button>

      <nav className="nav-links">
        <NavLink to="/simulation" className={({ isActive }) => (isActive ? 'active' : undefined)}>
          <MessageSquare size={22} />
          Simulation
        </NavLink>
        <NavLink to="/orchestration" className={({ isActive }) => (isActive ? 'active' : undefined)}>
          <Settings2 size={22} />
          Orchestration
        </NavLink>
      </nav>

      <section className="conversation-list">
        <p>Conversations</p>
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            onClick={async () => {
              await loadConversation(conversation.id)
              navigate('/simulation')
            }}
          >
            <span>{conversation.title || 'Untitled conversation'}</span>
            <small>{conversation.message_count} messages</small>
          </button>
        ))}
      </section>

      <div className="sidebar-bottom">
        <a href="/api/health" target="_blank" rel="noreferrer">
          <TerminalSquare size={21} />
          Logs
        </a>
        <a href="https://github.com/" target="_blank" rel="noreferrer">
          <BookOpen size={21} />
          Docs
        </a>
      </div>
    </aside>
  )
}

