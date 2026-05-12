import { Bot, Plus, Save } from 'lucide-react'
import { useEffect, useState } from 'react'

import AgentCard from '../components/AgentCard'
import AutoAgentDialog from '../components/AutoAgentDialog'
import PatternToggle from '../components/PatternToggle'
import PresetActions from '../components/PresetActions'
import { api } from '../lib/api'
import { useAppStore } from '../lib/store'
import type { AgentConfig } from '../lib/types'

export default function Orchestration() {
  const agents = useAppStore((state) => state.agents)
  const addAgent = useAppStore((state) => state.addAgent)
  const setAgents = useAppStore((state) => state.setAgents)
  const pattern = useAppStore((state) => state.pattern)
  const maxTurns = useAppStore((state) => state.maxTurns)
  const setMaxTurns = useAppStore((state) => state.setMaxTurns)
  const defaultModel = useAppStore((state) => state.defaultModel)
  const availableModels = useAppStore((state) => state.availableModels)
  const loadModels = useAppStore((state) => state.loadModels)
  const savePreset = useAppStore((state) => state.savePreset)
  const [theme, setTheme] = useState('')
  const [count, setCount] = useState<number | null>(null)
  const [autoModel, setAutoModel] = useState(defaultModel)
  const [generated, setGenerated] = useState<AgentConfig[] | null>(null)
  const [generating, setGenerating] = useState(false)
  const [autoError, setAutoError] = useState<string | null>(null)

  useEffect(() => {
    void loadModels()
  }, [loadModels])

  const description =
    pattern === 'free_flow'
      ? 'Free Flow: agents analyze context and interject naturally when relevant.'
      : 'Sequential: agents speak in the configured order, then repeat until max turns.'

  return (
    <div className="screen orchestration-screen">
      <header className="settings-header">
        <div>
          <h2>Orchestration Settings</h2>
          <p>Configure AI agent parameters, system prompts, and collaborative patterns.</p>
        </div>
        <PresetActions />
      </header>

      <section className="pattern-panel">
        <div className="section-label">
          <Bot size={18} />
          Global Pattern
        </div>
        <div className="pattern-grid">
          <div>
            <label className="field-label">Conversation Pattern</label>
            <PatternToggle />
          </div>
          <p>{description}</p>
          <label className="turn-input">
            Max Turns
            <input type="number" min={1} max={50} value={maxTurns} onChange={(event) => setMaxTurns(Number(event.target.value))} />
          </label>
        </div>
      </section>

      <section className="auto-panel">
        <div className="section-label">Auto Agent Creation</div>
        <textarea
          value={theme}
          placeholder="Describe the discussion theme..."
          onChange={(event) => setTheme(event.target.value)}
        />
        <div className="auto-controls">
          <div className="count-group">
            {[null, 1, 2, 3, 4, 5].map((value) => (
              <button key={value ?? 'auto'} className={count === value ? 'selected' : ''} onClick={() => setCount(value)}>
                {value ?? 'Auto'}
              </button>
            ))}
          </div>
          <select value={autoModel} onChange={(event) => setAutoModel(event.target.value)}>
            {availableModels.map((model) => (
              <option key={model}>{model}</option>
            ))}
          </select>
          <button
            className="primary-button"
            disabled={!theme.trim() || generating}
            onClick={async () => {
              setGenerating(true)
              setAutoError(null)
              try {
                const result = await api.autoAgents({ theme, count, model: autoModel })
                setGenerated(result.agents)
              } catch (error) {
                setAutoError(error instanceof Error ? error.message : String(error))
              } finally {
                setGenerating(false)
              }
            }}
          >
            {generating ? 'Generating...' : 'Generate'}
          </button>
        </div>
        {autoError && <p className="auto-error">{autoError}</p>}
      </section>

      <section className="active-header">
        <h3>Active Agents</h3>
        <button className="add-agent" onClick={addAgent}>
          <Plus size={19} />
          Add Agent
        </button>
      </section>

      <div className="agent-stack">
        {agents.map((agent, index) => (
          <AgentCard key={agent.id} agent={agent} index={index} />
        ))}
      </div>

      <div className="save-row">
        <button
          className="save-button"
          onClick={async () => {
            const name = window.prompt('Preset name', 'demo')
            if (name) {
              await savePreset(name)
            }
          }}
        >
          <Save size={22} />
          Save Configuration to JSON
        </button>
      </div>

      {generated && (
        <AutoAgentDialog
          agents={generated}
          onClose={() => setGenerated(null)}
          onAdopt={(items) => {
            setAgents(items)
            setGenerated(null)
          }}
        />
      )}
    </div>
  )
}
