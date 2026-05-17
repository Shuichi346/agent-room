import { Download, FileJson, FileText } from 'lucide-react'
import { useState } from 'react'

import { formatConversationJson, formatConversationMarkdown, type ConversationExportFormat } from '../lib/conversationExport'
import { useAppStore } from '../lib/store'

function triggerDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export default function ConversationDownload() {
  const [open, setOpen] = useState(false)
  const conversationId = useAppStore((state) => state.currentConversationId)
  const title = useAppStore((state) => state.currentConversationTitle)
  const messages = useAppStore((state) => state.messages)
  const buildPreset = useAppStore((state) => state.buildPreset)
  const hasMessages = messages.length > 0

  function download(format: ConversationExportFormat) {
    if (!hasMessages) return

    const input = {
      conversationId,
      title,
      preset: buildPreset(),
      messages,
    }
    const file = format === 'markdown' ? formatConversationMarkdown(input) : formatConversationJson(input)

    triggerDownload(file.content, file.filename, file.mimeType)
    setOpen(false)
  }

  return (
    <div className="download-menu">
      <button
        className="icon-action"
        type="button"
        title={hasMessages ? 'Download conversation' : 'No conversation to download'}
        aria-label="Download conversation"
        aria-expanded={open}
        aria-haspopup="menu"
        disabled={!hasMessages}
        onClick={() => setOpen((value) => !value)}
      >
        <Download size={20} />
      </button>
      {open && (
        <div className="download-popover" role="menu">
          <button type="button" role="menuitem" onClick={() => download('markdown')}>
            <FileText size={17} />
            Markdown
          </button>
          <button type="button" role="menuitem" onClick={() => download('json')}>
            <FileJson size={17} />
            JSON
          </button>
        </div>
      )}
    </div>
  )
}
