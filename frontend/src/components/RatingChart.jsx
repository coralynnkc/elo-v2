import { useState } from 'react'

const W = 880
const H = 260
const PAD = { top: 16, right: 16, bottom: 40, left: 44 }

// Rating after each round (chronological matches), plus the season-smoothed μ as a reference line
export default function RatingChart({ matches, seasonMu }) {
  const [hover, setHover] = useState(null)
  if (matches.length === 0) return null

  // Point 0 is the rating going into the first round
  const points = [
    { mu: matches[0].muBefore, match: null },
    ...matches.map(m => ({ mu: m.muAfter, match: m })),
  ]

  const values = points.map(p => p.mu).concat(seasonMu ?? [])
  const lo = Math.floor(Math.min(...values) - 1)
  const hi = Math.ceil(Math.max(...values) + 1)
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const x = i => PAD.left + (points.length === 1 ? plotW / 2 : (i / (points.length - 1)) * plotW)
  const y = v => PAD.top + (1 - (v - lo) / (hi - lo)) * plotH

  const ticks = niceTicks(lo, hi)
  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.mu).toFixed(1)}`).join('')

  // Tournament spans: first and last point index of each tournament's matches
  const spans = []
  matches.forEach((m, i) => {
    const last = spans[spans.length - 1]
    if (last && last.tournament === m.tournament) last.end = i + 1
    else spans.push({ tournament: m.tournament, name: m.tournamentName, start: i + 1, end: i + 1 })
  })

  // Tournament labels: centred under each span; a label that would collide with the
  // previous one on its row drops to the second row, or is skipped if both are taken
  const rowEnds = [-Infinity, -Infinity]
  spans.forEach((s, k) => {
    s.mid = (x(k === 0 ? 0 : s.start - 0.5) + x(s.end)) / 2
    const half = s.name.length * 3.3 + 4
    const row = rowEnds.findIndex(end => s.mid - half > end)
    s.row = row
    if (row >= 0) rowEnds[row] = s.mid + half
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
          aria-label={`Rating over ${matches.length} rounds, from ${points[0].mu.toFixed(1)} to ${points[points.length - 1].mu.toFixed(1)}`}
          onMouseMove={onMove}
          onMouseLeave={() => setHover(null)}
        >
          {ticks.map(t => (
            <g key={t}>
              <line className="grid" x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} />
              <text className="axis-label" x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end">{t}</text>
            </g>
          ))}

          {spans.map((s, k) => (
            <g key={s.tournament}>
              {k > 0 && (
                <line className="divider" x1={x(s.start - 0.5)} x2={x(s.start - 0.5)} y1={PAD.top} y2={H - PAD.bottom} />
              )}
              {s.row >= 0 && (
                <text className="axis-label" x={s.mid} y={H - PAD.bottom + 16 + s.row * 14} textAnchor="middle">
                  {s.name}
                </text>
              )}
            </g>
          ))}

          {seasonMu != null && (
            <line className="season-line" x1={PAD.left} x2={W - PAD.right} y1={y(seasonMu)} y2={y(seasonMu)} />
          )}

          <path className="rating-line" d={path} />

          {/* Drawn after the line so its halo sits on top */}
          {seasonMu != null && (
            <text className="axis-label" x={PAD.left + 6} y={y(seasonMu) - 6}>
              Season μ {seasonMu.toFixed(1)}
            </text>
          )}

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
            {hp.match ? (
              <>
                <div className="tt-title">{hp.match.roundDisplay}</div>
                <div>
                  <span className={hp.match.win ? 'win' : 'loss'}>{hp.match.win ? 'W' : 'L'}</span>
                  {' '}vs {hp.match.opponent} ({hp.match.side})
                </div>
                <div className="tt-value">
                  μ {hp.mu.toFixed(2)}{' '}
                  <span className="dim">({hp.match.delta > 0 ? '+' : ''}{hp.match.delta.toFixed(2)})</span>
                </div>
              </>
            ) : (
              <>
                <div className="tt-title">Start of season</div>
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
