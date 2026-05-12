import { RadioTower, Repeat2 } from 'lucide-react'

import { useAppStore } from '../lib/store'

export default function PatternToggle() {
  const pattern = useAppStore((state) => state.pattern)
  const setPattern = useAppStore((state) => state.setPattern)
  return (
    <div className="segmented">
      <button className={pattern === 'free_flow' ? 'selected' : ''} onClick={() => setPattern('free_flow')}>
        <RadioTower size={16} />
        Free Flow
      </button>
      <button className={pattern === 'round_robin' ? 'selected' : ''} onClick={() => setPattern('round_robin')}>
        <Repeat2 size={16} />
        Sequential
      </button>
    </div>
  )
}

