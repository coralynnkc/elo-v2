import { useState, useEffect } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { SEASONS, loadData, headToHead } from '../utils/data'
import SeasonHeader from '../components/SeasonHeader'

const SIZE = 16

// Cell fill from the row team's share of the meetings: blue when it leads the series,
// red when it trails, the plain surface at even. A split series runs 30–55% so a close one
// (3–2) still shows on the dark surface, and a sweep jumps to 75% so undefeated records
// stand apart; opacity stays below 1 so the text on it stays readable. The legend gradient
// in index.css uses the same stops.
function cellColor(w, l) {
  if (w === l) return 'var(--surface)'
  const share = w / (w + l)
  const margin = Math.abs(share - 0.5) * 2
  const strength = margin === 1 ? 75 : Math.round(30 + margin * 25)
  const hue = share > 0.5 ? 'var(--favored)' : 'var(--unfavored)'
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
        Each cell is how many times the <strong>row</strong> team beat the column team this
        season, with the full record underneath. Blank cells are pairs that haven't met.
      </p>

      <div className="matrix-legend" aria-hidden="true">
        <span>Row team trails</span>
        <span className="legend-bar" />
        <span>Row team leads</span>
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
                  const w = wins(row, col), l = wins(col, row)
                  if (w + l === 0) {
                    return (
                      <td
                        key={col.Team}
                        className="matrix-cell"
                        title={`${row.Team} and ${col.Team} haven't met this season`}
                        onMouseEnter={() => setHover({ i, j })}
                      />
                    )
                  }
                  return (
                    <td
                      key={col.Team}
                      className="matrix-cell"
                      style={{ background: cellColor(w, l) }}
                      title={`${row.Team} beat ${col.Team} ${w}× (${w}–${l} this season)`}
                      onMouseEnter={() => setHover({ i, j })}
                    >
                      <span className="matrix-p">{w}</span>
                      <span className="matrix-rec">{w}–{l}</span>
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
