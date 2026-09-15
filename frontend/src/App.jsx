import { HashRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import Leaderboard from './pages/Leaderboard'
import TeamPage from './pages/TeamPage'
import { CURRENT_SEASON } from './utils/data'

// Links shared before seasons existed (#/team/X) pointed at the 2025–26 rankings
function LegacyTeamRedirect() {
  const { teamName } = useParams()
  return <Navigate to={`/labor/team/${encodeURIComponent(teamName)}`} replace />
}

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Navigate to={`/${CURRENT_SEASON}`} replace />} />
        <Route path="/team/:teamName" element={<LegacyTeamRedirect />} />
        <Route path="/:season" element={<Leaderboard />} />
        <Route path="/:season/team/:teamName" element={<TeamPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  )
}
