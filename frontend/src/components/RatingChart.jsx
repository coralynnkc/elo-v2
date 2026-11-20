import { useState } from 'react'

const W = 880
const H = 260
const PAD = { top: 16, right: 16, bottom: 40, left: 44 }

// The rating after each tournament: the fit's estimate from the team's rounds so far
export default function RatingChart({ matches }) {
  const [hover, setHover] = useState(null)
  if (matches.length === 0) return null

  // Point 0 is the starting rating; then one point per tournament, in order
  const points = [{ mu: matches[0].muBefore, tournament: null }]
  for (const m of matches) {
    const last = points[points.length - 1]
    if (last.tournament === m.tournament) {
      last.mu = m.muAfter
      last.wins += m.win ? 1 : 0
      last.losses += m.win ? 0 : 1
    } else {
      points.push({
        mu: m.muAfter, tournament: m.tournament, name: m.tournamentName,
        before: last.mu, wins: m.win ? 1 : 0, losses: m.win ? 0 : 1,
      })
    }
  }

  const values = points.map(p => p.mu)
  const lo = Math.floor(Math.min(...values) - 1)
  const hi = Math.ceil(Math.max(...values) + 1)
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const x = i => PAD.left + (i / (points.length - 1)) * plotW
  const y = v => PAD.top + (1 - (v - lo) / (hi - lo)) * plotH

  const ticks = niceTicks(lo, hi)
  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.mu).toFixed(1)}`).join('')

  // Tournament labels under each point; a label that would collide with the previous
  // one on its row drops to the second row, or is skipped if both are taken
  const rowEnds = [-Infinity, -Infinity]
  points.forEach((p, i) => {
    if (!i) return
    const half = p.name.length * 3.3 + 4
    p.row = rowEnds.findIndex(end => x(i) - half > end)
    if (p.row >= 0) rowEnds[p.row] = x(i) + half
  })

  function onMove(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = ((e.clientX - rect.left) / rect.width) * W
    const i = Math.round(((px - PAD.left) / plotW) * (points.length - 1))
    setHover(Math.max(0, Math.min(points.length - 1, i)))
  }

  const hp = hover != null ? points[hover] : null

  return (
    <figure className="rating-chart">
      <div className="chart-box">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Rating over ${points.length - 1} tournaments, from ${points[0].mu.toFixed(1)} to ${points[points.length - 1].mu.toFixed(1)}`}
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
        >
          {ticks.map(t => (
            <g key={t}>
              <line className="grid" x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} />
              <text className="axis-label" x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end">{t}</text>
            </g>
          ))}

          {points.map((p, i) => i > 0 && p.row >= 0 && (
            <text key={p.tournament} className="axis-label" x={x(i)} y={H - PAD.bottom + 16 + p.row * 14}
              textAnchor={i === points.length - 1 ? 'end' : 'middle'}>
              {p.name}
            </text>
          ))}

          <path className="rating-line" d={path} />
          {points.map((p, i) => <circle key={i} className="point-dot" cx={x(i)} cy={y(p.mu)} r={3} />)}

          {hp && (
            <g>
              <line className="crosshair" x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={H - PAD.bottom} />
              <circle className="hover-dot" cx={x(hover)} cy={y(hp.mu)} r={5} />
            </g>
          )}
        </svg>

        {hp && (
          <div
            className="chart-tooltip"
            style={{
              left: `${(x(hover) / W) * 100}%`,
              top: `${(y(hp.mu) / H) * 100}%`,
              transform: `translate(${hover > points.length / 2 ? 'calc(-100% - 12px)' : '12px'}, -50%)`,
            }}
          >
            {hp.tournament ? (
              <>
                <div className="tt-title">{hp.name}</div>
                <div>
                  <span className="win">{hp.wins}</span>
                  <span className="dim">–</span>
                  <span className="loss">{hp.losses}</span>
                </div>
                <div className="tt-value">
                  μ {hp.mu.toFixed(2)}{' '}
                  <span className="dim">({hp.mu >= hp.before ? '+' : ''}{(hp.mu - hp.before).toFixed(2)})</span>
                </div>
              </>
            ) : (
              <>
                <div className="tt-title">{hp.mu === 25 ? 'Start of season' : 'Start of season (carried over)'}</div>
                <div className="tt-value">μ {hp.mu.toFixed(2)}</div>
              </>
            )}
          </div>
        )}
      </div>
    </figure>
  )
}

function niceTicks(lo, hi) {
  const range = hi - lo
  const step = range > 30 ? 10 : range > 12 ? 5 : range > 5 ? 2 : 1
  const ticks = []
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) ticks.push(t)
  return ticks
}
