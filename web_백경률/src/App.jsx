import { HashRouter, Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import Dashboard from './pages/Dashboard'
import RobotControl from './pages/RobotControl'
import LivePatrol from './pages/LivePatrol'
import LostItems from './pages/LostItems'
import LostItemDetail from './pages/LostItemDetail'
import { ToastProvider } from './hooks/useToast'

function App() {
  return (
    <ToastProvider>
      <HashRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<Dashboard />} />
            <Route path="robot-control" element={<RobotControl />} />
            <Route path="live-patrol" element={<LivePatrol />} />
            <Route path="lost-items" element={<LostItems />} />
            <Route path="lost-items/:id" element={<LostItemDetail />} />
          </Route>
        </Routes>
      </HashRouter>
    </ToastProvider>
  )
}

export default App
