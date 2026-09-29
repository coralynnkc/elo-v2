import { useState, useEffect } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { SEASONS, loadData, winProbability, headToHead } from '../utils/data'
import SeasonHeader from '../components/SeasonHeader'

const SIZE = 16

// Cell fill: blue when the row team is favoured, red when it isn't, fading to the
// surface at 50%. Opacity tops out below 1 so the text on it stays readable.
function cellColor(p) {
  const strength = Math.round(Math.abs(p - 0.5) * 2 * 70)
  const hue = p >= 0.5 ? 'var(--favored)' : 'var(--unfavored)'
  return `color-mix(in srgb, ${hue} ${strength}%, var(--surface))`
}

export default function HeadToHead() {
  const { season } = useParams()
  const [data, setData] = useState(null)
  const [hover, setHover] = useState(null)

  useEffect(() => {
    if (SEASONS[season]) loadData(season).then(d => setData({ season, ...d }))
  }, [season])

  if (!SEASONS[season]) return <Navigate to="/" replace />
  if (!data || data.season !== season) return <div className="loading">Loading…</div>

  const { teams, rawHistory } = data
  const top = teams.filter(t => t.Ranked).slice(0, SIZE)
  const h2h = headToHead(rawHistory)
  const wins = (a, b) => h2h[a.Team]?.[b.Team] ?? 0

  return (
    <div className="page">
      <SeasonHeader season={season} rawHistory={rawHistory} view="/h2h" />

      <p className="table-note">
        Each cell is the chance the <strong>row</strong> team beats the column team in one
        round, from season μ and σ. Where the two met this season, the row team's record
        against the column team is shown underneath.
      </p>

      <div className="matrix-legend" aria-hidden="true">
        <span>Row team unlikely</span>
        <span className="legend-bar" />
        <span>Row team likely</span>
      </div>

      <div className="table-wrap scroll">
        <table className="data-table matrix" onMouseLeave={() => setHover(null)}>
          <thead>
            <tr>
              <th className="matrix-corner">Team</th>
              {top.map((t, j) => (
                <th
                  key={t.Team}
                  className={`matrix-col${hover?.j === j ? ' is-hover' : ''}`}
                  title={t.Team}
                  scope="col"
                >
                  {j + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {top.map((row, i) => (
              <tr key={row.Team}>
                <th scope="row" className={`matrix-row${hover?.i === i ? ' is-hover' : ''}`}>
                  <span className="dim">{i + 1}</span>{' '}
                  <Link to={`/${season}/team/${encodeURIComponent(row.Team)}`}>{row.Team}</Link>
                </th>
                {top.map((col, j) => {
                  if (i === j) return <td key={col.Team} className="matrix-self" />
                  const p = winProbability(row, col)
                  const w = wins(row, col), l = wins(col, row)
                  const met = w + l > 0
                  const tip = `${row.Team} vs ${col.Team}: ${Math.round(p * 100)}%` +
                    (met ? ` · ${w}–${l} this season` : '')
                  return (
                    <td
                      key={col.Team}
                      className="matrix-cell"
                      style={{ background: cellColor(p) }}
                      title={tip}
                      onMouseEnter={() => setHover({ i, j })}
                    >
                      <span className="matrix-p">{Math.round(p * 100)}</span>
                      {met && (
                        <span className="matrix-rec">{w}–{l}</span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
