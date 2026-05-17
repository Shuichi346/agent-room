import { History, UserCircle, Wifi } from 'lucide-react'
import { useEffect } from 'react'

import ChatStream from '../components/ChatStream'
import ConversationDownload from '../components/ConversationDownload'
import PromptInput from '../components/PromptInput'
import { useAppStore } from '../lib/store'

export default function Simulation() {
  const pattern = useAppStore((state) => state.pattern)
  const loadModels = useAppStore((state) => state.loadModels)
  const modelError = useAppStore((state) => state.modelError)

  useEffect(() => {
    void loadModels()
  }, [loadModels])

  return (
    <div className="screen simulation-screen">
      <header className="topbar">
        <div />
        <h2>agent-room</h2>
        <div className="top-icons">
          <span className="status-pill">
            <i />
            {pattern === 'round_robin' ? 'Round Robin' : 'Free Flow'}
          </span>
          <ConversationDownload />
          <Wifi size={22} />
          <History size={23} />
          <UserCircle size={24} />
        </div>
      </header>
      {modelError && <div className="model-warning">No live model list from LM Studio. Using configured default model.</div>}
      <ChatStream />
      <PromptInput />
      <footer className="protocol-line">
        AGENT_ROOM_PROTOCOL_V0.1 // LOCAL CONNECTION
      </footer>
    </div>
  )
}
