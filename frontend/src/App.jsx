import { HashRouter, Routes, Route } from 'react-router-dom'
import Leaderboard from './pages/Leaderboard'
import TeamPage from './pages/TeamPage'

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Leaderboard />} />
        <Route path="/team/:teamName" element={<TeamPage />} />
      </Routes>
    </HashRouter>
  )
}
