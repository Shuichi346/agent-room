import { Link, Paperclip, Send, SlidersHorizontal, Square } from 'lucide-react'
import { useRef, useState } from 'react'

import { api } from '../lib/api'
import { useAppStore } from '../lib/store'
import type { Attachment } from '../lib/types'

export default function PromptInput() {
  const [prompt, setPrompt] = useState('')
  const [pending, setPending] = useState<Attachment[]>([])
  const [urlOpen, setUrlOpen] = useState(false)
  const [url, setUrl] = useState('')
  const fileRef = useRef<HTMLInputElement | null>(null)
  const runStatus = useAppStore((state) => state.runStatus)
  const startRun = useAppStore((state) => state.startRun)
  const cancelRun = useAppStore((state) => state.cancelRun)
  const buildPreset = useAppStore((state) => state.buildPreset)
  const currentConversationId = useAppStore((state) => state.currentConversationId)
  const maxTurns = useAppStore((state) => state.maxTurns)

  async function send() {
    if (!prompt.trim() || runStatus !== 'idle') return
    const text = prompt
    const attachments = pending
    setPrompt('')
    setPending([])
    await startRun({ preset: buildPreset(), prompt: text, attachments, conversation_id: currentConversationId })
  }

  return (
    <section className="prompt-dock">
      {pending.length > 0 && (
        <div className="pending-row">
          {pending.map((attachment, index) => (
            <button key={`${attachment.kind}-${index}`} onClick={() => setPending((items) => items.filter((_, itemIndex) => itemIndex !== index))}>
              {attachment.kind}: {attachment.source}
            </button>
          ))}
        </div>
      )}
      <textarea
        value={prompt}
        placeholder="Type a topic or steer the discussion..."
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
            void send()
          }
        }}
      />
      <div className="prompt-toolbar">
        <div className="prompt-tools">
          <button title="Attach image" onClick={() => fileRef.current?.click()}>
            <Paperclip size={19} />
          </button>
          <button title="Attach URL" onClick={() => setUrlOpen((value) => !value)}>
            <Link size={19} />
          </button>
          <button title={`Parameters: ${maxTurns} turns`}>
            <SlidersHorizontal size={18} />
            Parameters
          </button>
        </div>
        {runStatus === 'running' || runStatus === 'cancelling' ? (
          <button className="stop-button" onClick={() => void cancelRun()}>
            <Square size={18} />
          </button>
        ) : (
          <button className="send-button" onClick={() => void send()} disabled={!prompt.trim()}>
            <Send size={20} />
          </button>
        )}
      </div>
      {urlOpen && (
        <div className="url-popover">
          <input value={url} placeholder="https://example.com" onChange={(event) => setUrl(event.target.value)} />
          <button
            onClick={async () => {
              const attachment = await api.attachUrl(url)
              setPending((items) => [...items, attachment])
              setUrl('')
              setUrlOpen(false)
            }}
          >
            Attach
          </button>
        </div>
      )}
      <input
        ref={fileRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        hidden
        onChange={async (event) => {
          const file = event.target.files?.[0]
          if (file) {
            const attachment = await api.attachImage(file)
            setPending((items) => [...items, attachment])
          }
        }}
      />
    </section>
  )
}
