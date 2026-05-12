export type ConversationPattern = 'round_robin' | 'free_flow'

export interface AgentConfig {
  id: string
  name: string
  persona: string
  model: string
  color?: string | null
}

export interface Preset {
  id: string
  name: string
  agents: AgentConfig[]
  pattern: ConversationPattern
  max_turns: number
  auto_agent_model?: string | null
  created_at: string
  updated_at: string
}

export interface Attachment {
  kind: 'image' | 'url'
  payload: string
  source?: string | null
}

export interface Message {
  id: string
  agent_id?: string | null
  role: 'user' | 'assistant' | 'system'
  name: string
  content: string
  attachments: Attachment[]
  created_at: string
}

export interface Conversation {
  id: string
  title: string
  preset_snapshot: Preset
  messages: Message[]
  created_at: string
  updated_at: string
}

export interface ConversationSummary {
  id: string
  title: string
  updated_at: string
  message_count: number
}

export interface RunRequest {
  preset: Preset
  prompt: string
  attachments: Attachment[]
  conversation_id?: string | null
}

export interface AutoAgentRequest {
  theme: string
  count: number | null
  model: string
}

export interface AutoAgentResponse {
  agents: AgentConfig[]
}

export interface ModelResponse {
  models: string[]
  default: string
  error?: string
}

export type SSEEvent =
  | { type: 'conversation_started'; conversation_id: string; message: Message }
  | { type: 'message_start'; conversation_id: string; agent_id: string; name: string }
  | { type: 'message_complete'; conversation_id: string; message: Message; agent_id: string; name: string; content: string }
  | { type: 'done'; conversation_id: string; reason: string }
  | { type: 'cancelled'; conversation_id: string }
  | { type: 'error'; conversation_id?: string; message: string }

