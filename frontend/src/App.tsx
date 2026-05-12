import { Navigate, Route, Routes } from 'react-router-dom'

import Sidebar from './components/Sidebar'
import Orchestration from './routes/Orchestration'
import Simulation from './routes/Simulation'

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-shell">
        <Routes>
          <Route path="/" element={<Navigate to="/simulation" replace />} />
          <Route path="/simulation" element={<Simulation />} />
          <Route path="/orchestration" element={<Orchestration />} />
        </Routes>
      </main>
    </div>
  )
}

