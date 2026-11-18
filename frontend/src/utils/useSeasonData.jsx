import { useState, useEffect } from 'react'
import { SEASONS, loadData } from './data'

// A season's teams and history, or the error that stopped them loading. `data` is
// null until the requested season has loaded, so a page never shows the last season's.
export function useSeasonData(season) {
  const [state, setState] = useState({ season: null, data: null, error: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!SEASONS[season]) return
    let live = true
    setState({ season, data: null, error: null })
    loadData(season)
      .then(data => live && setState({ season, data, error: null }))
      .catch(error => live && setState({ season, data: null, error }))
    return () => { live = false }
  }, [season, attempt])

  const current = state.season === season
  return {
    data: current ? state.data : null,
    error: current ? state.error : null,
    retry: () => setAttempt(n => n + 1),
  }
}

export function LoadState({ error, retry }) {
  if (!error) return <div className="loading">Loading…</div>
  return (
    <div className="loading load-error">
      <p>Couldn’t load the ratings. Check your connection and try again.</p>
      <button type="button" className="retry-button" onClick={retry}>Retry</button>
    </div>
  )
}
