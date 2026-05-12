import { Download, Upload } from 'lucide-react'
import { useRef } from 'react'

import { api, exportPresetUrl } from '../lib/api'
import { useAppStore } from '../lib/store'

export default function PresetActions() {
  const fileRef = useRef<HTMLInputElement | null>(null)
  const currentPresetId = useAppStore((state) => state.currentPresetId)
  const loadPreset = useAppStore((state) => state.loadPreset)

  return (
    <div className="preset-actions">
      <button
        onClick={() => {
          if (currentPresetId) {
            window.location.href = exportPresetUrl(currentPresetId)
          }
        }}
        disabled={!currentPresetId}
      >
        <Download size={18} />
        Export JSON
      </button>
      <button onClick={() => fileRef.current?.click()}>
        <Upload size={18} />
        Import JSON
      </button>
      <input
        ref={fileRef}
        type="file"
        accept="application/json"
        hidden
        onChange={async (event) => {
          const file = event.target.files?.[0]
          if (file) {
            loadPreset(await api.importPreset(file))
          }
        }}
      />
    </div>
  )
}

