import { X } from 'lucide-react'
import { useState } from 'react'

import type { AgentConfig } from '../lib/types'

interface Props {
  agents: AgentConfig[]
  onAdopt: (agents: AgentConfig[]) => void
  onClose: () => void
}

export default function AutoAgentDialog({ agents, onAdopt, onClose }: Props) {
  const [draft, setDraft] = useState(agents)
  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-header">
          <h3>Generated Agents</h3>
          <button onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="auto-agent-list">
          {draft.map((agent) => (
            <div key={agent.id} className="auto-agent-row">
              <input
                value={agent.name}
                onChange={(event) =>
                  setDraft((items) => items.map((item) => (item.id === agent.id ? { ...item, name: event.target.value } : item)))
                }
              />
              <textarea
                value={agent.persona}
                onChange={(event) =>
                  setDraft((items) =>
                    items.map((item) => (item.id === agent.id ? { ...item, persona: event.target.value } : item)),
                  )
                }
              />
            </div>
          ))}
        </div>
        <div className="modal-actions">
          <button className="ghost-button" onClick={onClose}>
            Cancel
          </button>
          <button className="primary-button" onClick={() => onAdopt(draft)}>
            Adopt
          </button>
        </div>
      </div>
    </div>
  )
}

