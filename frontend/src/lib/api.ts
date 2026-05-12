import type {
  Attachment,
  AutoAgentRequest,
  AutoAgentResponse,
  Conversation,
  ConversationSummary,
  ModelResponse,
  Preset,
  RunRequest,
  SSEEvent,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `${response.status} ${response.statusText}`)
  }
  return (await response.json()) as T
}

export const api = {
  models: () => request<ModelResponse>('/api/models/'),
  presets: () => request<Preset[]>('/api/presets/'),
  savePreset: (preset: Preset) =>
    request<Preset>('/api/presets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preset),
    }),
  importPreset: async (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<Preset>('/api/presets/import', { method: 'POST', body })
  },
  conversations: () => request<ConversationSummary[]>('/api/conversations/'),
  conversation: (id: string) => request<Conversation>(`/api/conversations/${id}`),
  attachUrl: (url: string) =>
    request<Attachment>('/api/attachments/url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    }),
  attachImage: async (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<Attachment>('/api/attachments/image', { method: 'POST', body })
  },
  cancelRun: (id: string) => request<{ cancelled: boolean }>(`/api/chat/cancel/${id}`, { method: 'POST' }),
  autoAgents: (req: AutoAgentRequest) =>
    request<AutoAgentResponse>('/api/auto-agents/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }),
}

export async function* parseSSE(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.body) {
    throw new Error('Streaming response body is unavailable')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const dataLine = part
        .split('\n')
        .map((line) => line.trim())
        .find((line) => line.startsWith('data:'))
      if (dataLine) {
        yield JSON.parse(dataLine.slice(5).trim()) as SSEEvent
      }
    }
  }
}

export async function runChat(req: RunRequest, signal: AbortSignal): Promise<AsyncGenerator<SSEEvent>> {
  const response = await fetch(`${API_BASE}/api/chat/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return parseSSE(response)
}

export function exportPresetUrl(id: string): string {
  return `${API_BASE}/api/presets/${id}/export`
}

