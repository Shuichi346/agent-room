import type { Message, Preset } from './types'

export type ConversationExportFormat = 'markdown' | 'json'

interface ConversationExportInput {
  conversationId: string | null
  title: string
  preset: Preset
  messages: Message[]
}

interface ConversationExportPayload extends ConversationExportInput {
  exportedAt: string
}

const fallbackTitle = 'Conversation history'

function cleanTitle(title: string): string {
  return title.trim() || fallbackTitle
}

function filenameTimestamp(value: string): string {
  return value.replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z')
}

function slugifyTitle(title: string): string {
  const slug = cleanTitle(title)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 48)

  return slug || 'conversation'
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatAttachment(message: Message): string {
  if (message.attachments.length === 0) {
    return ''
  }

  const items = message.attachments.map((attachment) => {
    const label = attachment.kind === 'url' ? 'URL' : 'Image'
    const source = attachment.source ?? attachment.payload
    return `- ${label}: ${source}`
  })

  return `\n\nAttachments:\n${items.join('\n')}`
}

function buildPayload(input: ConversationExportInput): ConversationExportPayload {
  return {
    ...input,
    title: cleanTitle(input.title),
    exportedAt: new Date().toISOString(),
  }
}

export function getConversationExportFilename(title: string, format: ConversationExportFormat, exportedAt: string): string {
  const extension = format === 'markdown' ? 'md' : 'json'
  return `${slugifyTitle(title)}-${filenameTimestamp(exportedAt)}.${extension}`
}

export function formatConversationMarkdown(input: ConversationExportInput): { content: string; filename: string; mimeType: string } {
  const payload = buildPayload(input)
  const lines = [
    `# ${payload.title}`,
    '',
    `- Conversation ID: ${payload.conversationId ?? 'Unsaved'}`,
    `- Exported: ${formatDate(payload.exportedAt)}`,
    `- Preset: ${payload.preset.name}`,
    `- Pattern: ${payload.preset.pattern === 'round_robin' ? 'Round Robin' : 'Free Flow'}`,
    `- Messages: ${payload.messages.length}`,
    '',
    '## Messages',
    '',
    ...payload.messages.map((message, index) => {
      const headingName = message.name.replace(/\s+/g, ' ').trim() || message.role
      const body = message.content.trim() || '(empty message)'
      return [
        `### ${index + 1}. ${headingName} (${message.role})`,
        '',
        `Time: ${formatDate(message.created_at)}`,
        '',
        body,
        formatAttachment(message),
      ].join('\n')
    }),
    '',
  ]

  return {
    content: lines.join('\n'),
    filename: getConversationExportFilename(payload.title, 'markdown', payload.exportedAt),
    mimeType: 'text/markdown;charset=utf-8',
  }
}

export function formatConversationJson(input: ConversationExportInput): { content: string; filename: string; mimeType: string } {
  const payload = buildPayload(input)
  const content = JSON.stringify(
    {
      conversation_id: payload.conversationId,
      title: payload.title,
      exported_at: payload.exportedAt,
      preset_snapshot: payload.preset,
      messages: payload.messages,
    },
    null,
    2,
  )

  return {
    content,
    filename: getConversationExportFilename(payload.title, 'json', payload.exportedAt),
    mimeType: 'application/json;charset=utf-8',
  }
}
