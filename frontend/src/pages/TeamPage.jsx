import { useState, useEffect } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { SEASONS, getTeamMatches, otherSeasonTeams } from '../utils/data'
import { useSeasonData, LoadState } from '../utils/useSeasonData'
import RatingChart from '../components/RatingChart'

function record(matches) {
  const wins = matches.filter(m => m.win).length
  return { wins, losses: matches.length - wins }
}

function Record({ wins, losses }) {
  return (
    <>
      <span className="win">{wins}</span>
      <span className="dim">–</span>
      <span className="loss">{losses}</span>
    </>
  )
}

function Delta({ value }) {
  // Anything that rounds to 0.00 reads as no change
  if (Math.abs(value) < 0.005) return <span className="dim">0.00</span>
  return (
    <span className={value > 0 ? 'positive' : 'negative'}>
      {value > 0 ? '+' : ''}{value.toFixed(2)}
    </span>
  )
}

function MatchRow({ m, season, oppMu }) {
  return (
    <tr>
      <td>{m.roundDisplay}</td>
      <td>
        <Link to={`/${season}/team/${encodeURIComponent(m.opponent)}`}>{m.opponent}</Link>
      </td>
      <td>{m.side}</td>
      <td className={m.win ? 'win' : 'loss'}>{m.win ? 'Win' : 'Loss'}</td>
      <td className="num dim">{oppMu[m.opponent]?.toFixed(2) ?? '–'}</td>
      <td className="num"><Delta value={m.delta} /></td>
    </tr>
  )
}

export default function TeamPage() {
  const { season, teamName } = useParams()
  const name = decodeURIComponent(teamName)
  const { data, error, retry } = useSeasonData(season)
  const [sortBy, setSortBy] = useState('chronological')
  const [open, setOpen] = useState(null)
  const [others, setOthers] = useState([])

  const team = data?.teams.find(t => t.Team === name)

  useEffect(() => {
    setOthers([])
    setOpen(null)
    if (team) otherSeasonTeams(season, team).then(setOthers)
  }, [season, team])

  if (!SEASONS[season]) return <Navigate to="/" replace />
  if (!data) return <LoadState error={error} retry={retry} />

  const { teams, rawHistory } = data
  const ranked = teams.filter(t => t.Ranked)
  const rank = team?.Ranked ? ranked.indexOf(team) + 1 : null
  const matches = getTeamMatches(rawHistory, name)
  const overall = record(matches)
  const aff = record(matches.filter(m => m.side === 'Aff'))
  const neg = record(matches.filter(m => m.side === 'Neg'))

  // Tournaments newest first, rounds within each in the order they were debated
  const groups = []
  for (const m of matches) {
    const last = groups[groups.length - 1]
    if (last?.tournament === m.tournament) last.matches.push(m)
    else groups.push({ tournament: m.tournament, name: m.tournamentName, matches: [m] })
  }
  groups.reverse()
  // Only the latest tournament starts open
  const openSet = open ?? new Set(groups.slice(0, 1).map(g => g.tournament))
  function toggleGroup(tournament) {
    const next = new Set(openSet)
    next.has(tournament) ? next.delete(tournament) : next.add(tournament)
    setOpen(next)
  }
  const allOpen = groups.every(g => openSet.has(g.tournament))

  const consequential = [...matches].sort((a, b) => b.absDelta - a.absDelta)
  const oppMu = Object.fromEntries(teams.map(t => [t.Team, t.Mu]))

  return (
    <div className="page">
      <div className="back-link">
        <Link to={`/${season}`}>← {SEASONS[season].label} Rankings</Link>
      </div>

      <header className="team-header">
        <h1>{name}</h1>
        {team?.Debaters && <p className="subtitle">{team.Debaters}</p>}
        {rank && <span className="team-rank">Ranked #{rank} of {ranked.length}</span>}
        {team && !team.Ranked && (
          <span className="team-rank">
            Unranked · {team.Tournaments} tournament{team.Tournaments === 1 ? '' : 's'}
          </span>
        )}
        {others.length > 0 && (
          <p className="other-seasons">
            <span className="dim">Other seasons: </span>
            {others.map(({ season: s, team: t, shared }, i) => (
              <span key={`${s}/${t.Team}`}>
                {i > 0 && <span className="dim"> · </span>}
                <Link to={`/${s}/team/${encodeURIComponent(t.Team)}`}>{t.Team}</Link>
                <span className="dim">
                  {' '}{SEASONS[s].label}
                  {shared.length < 2 && ` (${shared[0]})`}
                </span>
              </span>
            ))}
          </p>
        )}
      </header>

      {team && (
        <div className="stat-cards">
          <div className="stat-card">
            <div className="stat-label has-tip" tabIndex={0}
              data-tip="The model's best estimate of team strength, fitted on the whole season. ± is σ, the uncertainty">
              Rating (<span className="greek">μ</span>)
            </div>
            <div className="stat-value">
              {team.Mu.toFixed(2)}
              <span className="stat-sub"> ± {team.Sigma.toFixed(2)}</span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label has-tip" tabIndex={0}
              data-tip="μ − 3σ: a rating the team very likely exceeds">
              Conservative
            </div>
            <div className="stat-value">{team.Conservative.toFixed(2)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Record</div>
            <div className="stat-value"><Record {...overall} /></div>
            <div className="stat-split">
              Aff <Record {...aff} /> · Neg <Record {...neg} />
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Tournaments</div>
            <div className="stat-value">{team.Tournaments}</div>
          </div>
        </div>
      )}

      {matches.length > 0 && (
        <>
          <div className="section-header">
            <h2>Rating Over the Season</h2>
          </div>
          <RatingChart matches={matches} />
        </>
      )}

      <div className="section-header">
        <h2>Match History</h2>
        <div className="sort-toggle">
          <button
            className={sortBy === 'chronological' ? 'active' : ''}
            onClick={() => setSortBy('chronological')}
          >
            By Tournament
          </button>
          <button
            className={sortBy === 'consequential' ? 'active' : ''}
            onClick={() => setSortBy('consequential')}
          >
            Most Consequential
          </button>
        </div>
      </div>

      <p className="table-note">
        Each round's Δ is its effect on the team's end-of-season rating: roughly what the
        rating would lose without that round, or gain if it's red. Unexpected results count
        most, so beating a higher-rated opponent (Opp. μ) helps more, and losing to a
        lower-rated one hurts more. A tournament's total adds
        up its rounds' Δ. It won't match that tournament's step on the chart, which shows the
        rating as it stood at the time, when early results moved it most, while Δ weighs each
        round with the whole season known.
        {sortBy === 'chronological' && groups.length > 1 && (
          <>
            {' '}
            <button
              type="button"
              className="link-button"
              onClick={() => setOpen(new Set(allOpen ? [] : groups.map(g => g.tournament)))}
            >
              {allOpen ? 'Collapse all' : 'Expand all'}
            </button>
          </>
        )}
      </p>

      <div className="table-wrap">
        <table className="data-table match-table">
          <thead>
            <tr>
              <th>Round</th>
              <th>Opponent</th>
              <th>Side</th>
              <th>Result</th>
              <th className="align-right has-tip" data-tip="The opponent's whole-season rating">Opp. <span className="greek">μ</span></th>
              <th className="align-right">Δ Rating</th>
            </tr>
          </thead>
          {sortBy === 'consequential' ? (
            <tbody>
              {consequential.map((m, i) => <MatchRow key={i} m={m} season={season} oppMu={oppMu} />)}
            </tbody>
          ) : (
            groups.map(g => {
              const isOpen = openSet.has(g.tournament)
              const net = g.matches.reduce((sum, m) => sum + m.delta, 0)
              return (
                <tbody key={g.tournament}>
                  <tr className="group-row">
                    <td colSpan={6}>
                      <button
                        type="button"
                        aria-expanded={isOpen}
                        onClick={() => toggleGroup(g.tournament)}
                      >
                        <span className="group-caret" aria-hidden="true">{isOpen ? '▾' : '▸'}</span>
                        <span className="group-name">{g.name}</span>
                        <span className="group-record"><Record {...record(g.matches)} /></span>
                        <span className="group-delta num align-right"><Delta value={net} /></span>
                      </button>
                    </td>
                  </tr>
                  {isOpen && g.matches.map((m, i) => <MatchRow key={i} m={m} season={season} oppMu={oppMu} />)}
                </tbody>
              )
            })
          )}
        </table>
      </div>
    </div>
  )
}
