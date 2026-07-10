import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import FVGReport from './pages/FVGReport'
import PowerOf3 from './pages/PowerOf3'
import Macros from './pages/Macros'
import GEXLevels from './pages/GEXLevels'
import OIByStrike from './pages/OIByStrike'
import PutCallRatio from './pages/PutCallRatio'

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center h-64 text-muted">
      {title} — coming soon
    </div>
  )
}

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/reports/fvg" replace />} />
        <Route path="/reports/fvg" element={<FVGReport />} />
        <Route path="/reports/power-of-3" element={<PowerOf3 />} />
        <Route path="/reports/macros" element={<Macros />} />
        <Route path="/reports/:slug" element={<PlaceholderPage title="Report" />} />
        <Route path="/options/gex-levels" element={<GEXLevels />} />
        <Route path="/options/oi-by-strike" element={<OIByStrike />} />
        <Route path="/options/put-call-ratio" element={<PutCallRatio />} />
        <Route path="/options/:slug" element={<PlaceholderPage title="Options" />} />
        <Route path="/qt/:slug" element={<PlaceholderPage title="QT Report" />} />
      </Routes>
    </AppShell>
  )
}
