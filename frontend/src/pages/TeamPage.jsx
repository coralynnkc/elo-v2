import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { loadData, getTeamMatches } from '../utils/data'

export default function TeamPage() {
  const { teamName } = useParams()
  const name = decodeURIComponent(teamName)
  const [data, setData] = useState(null)
  const [sortBy, setSortBy] = useState('consequential')

  useEffect(() => { loadData().then(setData) }, [])

  if (!data) return <div className="loading">Loading…</div>

  const { teams, rawHistory } = data
  const team = teams.find(t => t.Team === name)
  const rank = team ? teams.indexOf(team) + 1 : null
  const matches = getTeamMatches(rawHistory, name)

  const affWins = matches.filter(m => m.side === 'Aff' && m.win).length
  const affLosses = matches.filter(m => m.side === 'Aff' && !m.win).length
  const negWins = matches.filter(m => m.side === 'Neg' && m.win).length
  const negLosses = matches.filter(m => m.side === 'Neg' && !m.win).length

  const sorted = sortBy === 'consequential'
    ? [...matches].sort((a, b) => b.absDelta - a.absDelta)
    : matches

  return (
    <div className="page">
      <div className="back-link">
        <Link to="/">← Rankings</Link>
      </div>

      <header className="team-header">
        <h1>{name}</h1>
        {rank && <span className="team-rank">Ranked #{rank} of {teams.length}</span>}
      </header>

      {team && (
        <div className="stat-cards">
          <div className="stat-card">
            <div className="stat-label">Rating (μ)</div>
            <div className="stat-value">{team.Mu}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Conservative</div>
            <div className="stat-value">{team.Conservative}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Aff Record</div>
            <div className="stat-value">
              <span className="win">{affWins}</span>
              <span className="dim">–</span>
              <span className="loss">{affLosses}</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Neg Record</div>
            <div className="stat-value">
              <span className="win">{negWins}</span>
              <span className="dim">–</span>
              <span className="loss">{negLosses}</span>
            </div>
          </div>
        </div>
      )}

      <div className="section-header">
        <h2>Match History</h2>
        <div className="sort-toggle">
          <button
            className={sortBy === 'consequential' ? 'active' : ''}
            onClick={() => setSortBy('consequential')}
          >
            Most Consequential
          </button>
          <button
            className={sortBy === 'chronological' ? 'active' : ''}
            onClick={() => setSortBy('chronological')}
          >
            Chronological
          </button>
        </div>
      </div>

      <div className="table-wrap">
        <table className="match-table">
          <thead>
            <tr>
              <th>Round</th>
              <th>Opponent</th>
              <th>Side</th>
              <th>Result</th>
              <th className="align-right">Before</th>
              <th className="align-right">After</th>
              <th className="align-right">Δ Rating</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((m, i) => (
              <tr key={i}>
                <td>{m.roundDisplay}</td>
                <td>
                  <Link to={`/team/${encodeURIComponent(m.opponent)}`}>
                    {m.opponent}
                  </Link>
                </td>
                <td>{m.side}</td>
                <td className={m.win ? 'win' : 'loss'}>{m.win ? 'Win' : 'Loss'}</td>
                <td className="num">{m.muBefore.toFixed(3)}</td>
                <td className="num">{m.muAfter.toFixed(3)}</td>
                <td className={`num ${m.delta > 0 ? 'positive' : 'negative'}`}>
                  {m.delta > 0 ? '+' : ''}{m.delta.toFixed(3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
