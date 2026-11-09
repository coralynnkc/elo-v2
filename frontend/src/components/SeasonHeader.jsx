import { NavLink, useNavigate } from 'react-router-dom'
import { SEASONS, getTournaments } from '../utils/data'

// Title, season switcher, subtitle and view tabs shared by the leaderboard and H2H pages.
// view is the path after the season ('' for rankings, '/h2h'); switching seasons keeps it.
export default function SeasonHeader({ season, rawHistory, view }) {
  const tournaments = getTournaments(rawHistory)
  const latest = tournaments[tournaments.length - 1]
  const navigate = useNavigate()

  return (
    <header className="page-header">
      <h1>Policy Debate Rankings</h1>
      <nav className="season-nav" aria-label="Season">
        {Object.entries(SEASONS).map(([key, s]) => (
          <NavLink key={key} to={`/${key}${view}`}>
            {s.label}
          </NavLink>
        ))}
      </nav>
      {/* Phones get a dropdown instead of the pill bar */}
      <select
        className="season-select"
        aria-label="Season"
        value={season}
        onChange={e => navigate(`/${e.target.value}${view}`)}
      >
        {Object.entries(SEASONS).map(([key, s]) => (
          <option key={key} value={key}>{s.label}</option>
        ))}
      </select>
      <p className="subtitle">
        TrueSkill Through Time ratings ·{' '}
        <span className="has-tip" tabIndex={0} data-tip={tournaments.join(' → ')}>
          through {latest} ({tournaments.length} tournament{tournaments.length === 1 ? '' : 's'})
        </span>
      </p>
      {tournaments.length < 2 && (
        <p className="provisional">
          Provisional — based on one tournament. Ratings and σ will settle as more
          tournaments are added.
        </p>
      )}
      <nav className="view-tabs" aria-label="View">
        <NavLink to={`/${season}`} end>Rankings</NavLink>
        <NavLink to={`/${season}/h2h`}>Head-to-head</NavLink>
      </nav>
    </header>
  )
}
