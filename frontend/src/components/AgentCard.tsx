import { Trash2 } from 'lucide-react'
import type { CSSProperties } from 'react'

import type { AgentConfig } from '../lib/types'
import { useAppStore } from '../lib/store'

interface Props {
  agent: AgentConfig
  index: number
}

export default function AgentCard({ agent, index }: Props) {
  const updateAgent = useAppStore((state) => state.updateAgent)
  const removeAgent = useAppStore((state) => state.removeAgent)
  const models = useAppStore((state) => state.availableModels)
  const canRemove = useAppStore((state) => state.agents.length > 1)

  return (
    <article className="agent-card" style={{ '--agent-color': agent.color ?? '#08D9C7' } as CSSProperties}>
      <div className="agent-left">
        <div className="agent-avatar">{agent.name.slice(0, 1) || index + 1}</div>
        <button className="remove-agent" disabled={!canRemove} onClick={() => removeAgent(agent.id)}>
          <Trash2 size={15} />
          Remove
        </button>
      </div>
      <div className="agent-fields">
        <label>
          Agent Name
          <input value={agent.name} onChange={(event) => updateAgent(agent.id, { name: event.target.value })} />
        </label>
        <label>
          Model Engine
          <select value={agent.model} onChange={(event) => updateAgent(agent.id, { model: event.target.value })}>
            {models.map((model) => (
              <option key={model}>{model}</option>
            ))}
          </select>
        </label>
        <label className="persona-label">
          System Persona (Prompt)
          <textarea value={agent.persona} onChange={(event) => updateAgent(agent.id, { persona: event.target.value })} />
        </label>
      </div>
    </article>
  )
}
