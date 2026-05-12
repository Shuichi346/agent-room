import { create } from 'zustand'

import { api, runChat } from './api'
import type { AgentConfig, ConversationSummary, Message, Preset, RunRequest } from './types'

const now = () => new Date().toISOString()
const colors = ['#08D9C7', '#B48CFF', '#FF4D5B', '#0FA89A', '#00AEEF']

function id() {
  return crypto.randomUUID()
}

export function defaultAgents(model = 'google/gemma-4-e2b'): AgentConfig[] {
  return [
    {
      id: id(),
      name: 'Architect',
      persona:
        'You are the Architect. You focus on structure, scalability, trade-offs, and the shape of the solution before implementation details.',
      model,
      color: '#08D9C7',
    },
    {
      id: id(),
      name: 'Synthesizer',
      persona:
        'You are the Synthesizer. You turn other agents ideas into crisp, actionable conclusions with clear next steps.',
      model,
      color: '#B48CFF',
    },
    {
      id: id(),
      name: 'Validator',
      persona:
        'You are the Validator. You challenge weak assumptions, look for risks, and make sure the final direction is defensible.',
      model,
      color: '#FF4D5B',
    },
  ]
}

interface AppState {
  agents: AgentConfig[]
  pattern: 'round_robin' | 'free_flow'
  maxTurns: number
  defaultModel: string
  availableModels: string[]
  modelError: string | null
  currentPresetId: string | null
  currentPresetName: string
  conversations: ConversationSummary[]
  currentConversationId: string | null
  messages: Message[]
  runStatus: 'idle' | 'running' | 'cancelling'
  abortController: AbortController | null
  addAgent: () => void
  removeAgent: (agentId: string) => void
  updateAgent: (agentId: string, patch: Partial<AgentConfig>) => void
  setPattern: (pattern: 'round_robin' | 'free_flow') => void
  setMaxTurns: (value: number) => void
  setAgents: (agents: AgentConfig[]) => void
  clearConversation: () => void
  loadModels: () => Promise<void>
  loadConversations: () => Promise<void>
  loadConversation: (id: string) => Promise<void>
  buildPreset: (name?: string) => Preset
  savePreset: (name: string) => Promise<Preset>
  loadPreset: (preset: Preset) => void
  startRun: (req: RunRequest) => Promise<void>
  cancelRun: () => Promise<void>
}

export const useAppStore = create<AppState>((set, get) => ({
  agents: defaultAgents(),
  pattern: 'round_robin',
  maxTurns: 10,
  defaultModel: 'google/gemma-4-e2b',
  availableModels: ['google/gemma-4-e2b'],
  modelError: null,
  currentPresetId: null,
  currentPresetName: 'Working preset',
  conversations: [],
  currentConversationId: null,
  messages: [],
  runStatus: 'idle',
  abortController: null,
  addAgent: () =>
    set((state) => ({
      agents: [
        ...state.agents,
        {
          id: id(),
          name: `Agent ${state.agents.length + 1}`,
          persona: 'You are a focused discussion agent. Add one useful perspective to the conversation.',
          model: state.defaultModel,
          color: colors[state.agents.length % colors.length],
        },
      ],
    })),
  removeAgent: (agentId) => set((state) => ({ agents: state.agents.filter((agent) => agent.id !== agentId) })),
  updateAgent: (agentId, patch) =>
    set((state) => ({
      agents: state.agents.map((agent) => (agent.id === agentId ? { ...agent, ...patch } : agent)),
    })),
  setPattern: (pattern) => set({ pattern }),
  setMaxTurns: (value) => set({ maxTurns: Math.min(50, Math.max(1, value)) }),
  setAgents: (agents) => set({ agents }),
  clearConversation: () => set({ currentConversationId: null, messages: [] }),
  loadModels: async () => {
    const result = await api.models()
    const models = result.models.length ? result.models : [result.default]
    set({
      defaultModel: result.default,
      availableModels: models,
      modelError: result.error ?? null,
      agents: get().agents.map((agent) => ({ ...agent, model: agent.model || result.default })),
    })
  },
  loadConversations: async () => set({ conversations: await api.conversations() }),
  loadConversation: async (conversationId) => {
    const conversation = await api.conversation(conversationId)
    set({
      currentConversationId: conversation.id,
      messages: conversation.messages,
      currentPresetId: conversation.preset_snapshot.id,
      currentPresetName: conversation.preset_snapshot.name,
      agents: conversation.preset_snapshot.agents,
      pattern: conversation.preset_snapshot.pattern,
      maxTurns: conversation.preset_snapshot.max_turns,
    })
  },
  buildPreset: (name = get().currentPresetName) => ({
    id: get().currentPresetId ?? '',
    name,
    agents: get().agents,
    pattern: get().pattern,
    max_turns: get().maxTurns,
    auto_agent_model: get().defaultModel,
    created_at: now(),
    updated_at: now(),
  }),
  savePreset: async (name) => {
    const preset = await api.savePreset(get().buildPreset(name))
    set({ currentPresetId: preset.id, currentPresetName: preset.name })
    return preset
  },
  loadPreset: (preset) =>
    set({
      currentPresetId: preset.id,
      currentPresetName: preset.name,
      agents: preset.agents,
      pattern: preset.pattern,
      maxTurns: preset.max_turns,
    }),
  startRun: async (req) => {
    const controller = new AbortController()
    set({ runStatus: 'running', abortController: controller })
    try {
      const stream = await runChat(req, controller.signal)
      for await (const event of stream) {
        if (event.type === 'conversation_started') {
          set((state) => ({
            currentConversationId: event.conversation_id,
            messages: [...state.messages, event.message],
          }))
        }
        if (event.type === 'message_complete') {
          set((state) => ({
            currentConversationId: event.conversation_id,
            messages: [...state.messages, event.message],
          }))
        }
        if (event.type === 'error') {
          const message: Message = {
            id: id(),
            role: 'system',
            name: 'System',
            content: event.message,
            attachments: [],
            created_at: now(),
          }
          set((state) => ({ messages: [...state.messages, message] }))
        }
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        const message: Message = {
          id: id(),
          role: 'system',
          name: 'System',
          content: error instanceof Error ? error.message : String(error),
          attachments: [],
          created_at: now(),
        }
        set((state) => ({ messages: [...state.messages, message] }))
      }
    } finally {
      set({ runStatus: 'idle', abortController: null })
      await get().loadConversations()
    }
  },
  cancelRun: async () => {
    const { currentConversationId, abortController } = get()
    set({ runStatus: 'cancelling' })
    if (currentConversationId) {
      await api.cancelRun(currentConversationId).catch(() => undefined)
    }
    abortController?.abort()
    set({ runStatus: 'idle', abortController: null })
  },
}))

