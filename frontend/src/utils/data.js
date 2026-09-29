import Papa from 'papaparse'

export const CURRENT_SEASON = 'arms'

// Keys and file names match SEASONS in coding/pipeline.py; listed newest first
export const SEASONS = {
  arms: { label: '2026–27', teams: 'teams_arms.csv', history: 'match_history_arms.csv' },
  labor: { label: '2025–26', teams: 'teams_labor.csv', history: 'match_history.csv' },
  energy: { label: '2024–25', teams: 'teams_energy.csv', history: 'match_history_energy.csv' },
}

const TOURNAMENT_NAMES = {
  nu: 'Northwestern',
  kentuckyrr: 'Kentucky RR',
  uk: 'Kentucky',
  gonzaga: 'Gonzaga',
  wake: 'Wake Forest',
  gt: 'Georgetown',
  georgetown: 'Georgetown',
  harvard: 'Harvard',
  dartmouthrr: 'Dartmouth RR',
  texas: 'Texas',
  ada: 'ADA',
  ndt: 'NDT',
}

const ELIM_LABELS = {
  dubs: 'Doubles',
  octas: 'Octafinals',
  quarters: 'Quarterfinals',
  semis: 'Semifinals',
  semis_2: 'Third Place',
  finals: 'Finals',
}

export function tournamentName(tournament) {
  return TOURNAMENT_NAMES[tournament] || tournament.toUpperCase()
}

export function formatRound(tournament, roundLabel) {
  const r = isNaN(Number(roundLabel))
    ? (ELIM_LABELS[roundLabel] || roundLabel)
    : `R${roundLabel}`
  return `${tournamentName(tournament)} ${r}`
}

// Tournament display names in chronological order (history rows are chronological)
export function getTournaments(rawHistory) {
  return [...new Set(rawHistory.map(m => m.Tournament))].map(tournamentName)
}

// One parse per file, shared by every caller
const _files = {}

function parseCsv(file) {
  _files[file] ??= fetch(`${import.meta.env.BASE_URL}data/${file}`)
    .then(res => res.text())
    .then(text => Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true }).data)
  return _files[file]
}

export async function loadTeams(season) {
  const teams = await parseCsv(SEASONS[season].teams)
  // Teams below the pipeline's MIN_TOURNAMENTS are exported with Ranked = False
  for (const t of teams) t.Ranked = t.Ranked !== false && t.Ranked !== 'False'
  return teams
}

export async function loadData(season) {
  const [teams, rawHistory] = await Promise.all([
    loadTeams(season),
    parseCsv(SEASONS[season].history),
  ])
  return { teams, rawHistory }
}

// Wins by each team over each opponent: h2h[winner][loser] = count
export function headToHead(rawHistory) {
  const h2h = {}
  for (const m of rawHistory) {
    if (m.Win !== 'Aff' && m.Win !== 'Neg') continue
    const [w, l] = m.Win === 'Aff' ? [m.Aff, m.Neg] : [m.Neg, m.Aff]
    h2h[w] ??= {}
    h2h[w][l] = (h2h[w][l] ?? 0) + 1
  }
  return h2h
}

function normalizeSurname(name) {
  return name.normalize('NFKD').replace(/[^a-z]/gi, '').toLowerCase()
}

// Frontend approximation of the pipeline's School/surname debater keys. Team names are
// "School XY" or "School XY (A/B)"; a hybrid's school is "A/B", and each debater could
// belong to either half, so a debater gets one key per school.
export function debaterKeys(team) {
  if (!team.Debaters) return []
  const schools = team.Team.replace(/ \(.*\)$/, '').replace(/ \S+$/, '').split('/')
  return team.Debaters.split(' & ').map(name => ({
    name,
    keys: schools.map(school => `${school}/${normalizeSurname(name)}`),
  }))
}

// Teams in other seasons sharing a debater with this one, newest season first
export async function otherSeasonTeams(season, team) {
  const debaters = debaterKeys(team)
  if (debaters.length === 0) return []
  const found = []
  for (const other of Object.keys(SEASONS)) {
    if (other === season) continue
    let teams
    try { teams = await loadTeams(other) } catch { continue }
    for (const t of teams) {
      const theirs = new Set(debaterKeys(t).flatMap(d => d.keys))
      const shared = debaters.filter(d => d.keys.some(k => theirs.has(k))).map(d => d.name)
      if (shared.length) found.push({ season: other, team: t, shared })
    }
  }
  return found
}

export function getTeamMatches(rawHistory, teamName) {
  return rawHistory
    .filter(m => m.Aff === teamName || m.Neg === teamName)
    .map(m => {
      const isAff = m.Aff === teamName
      const delta = isAff ? m.Aff_Mu_Delta : m.Neg_Mu_Delta
      return {
        round: m.Round,
        tournament: m.Tournament,
        tournamentName: tournamentName(m.Tournament),
        roundLabel: m.Round_Label,
        roundDisplay: formatRound(m.Tournament, String(m.Round_Label)),
        side: isAff ? 'Aff' : 'Neg',
        opponent: isAff ? m.Neg : m.Aff,
        win: m.Win === (isAff ? 'Aff' : 'Neg'),
        delta,
        muBefore: isAff ? m.Aff_Mu_Before : m.Neg_Mu_Before,
        muAfter: isAff ? m.Aff_Mu_After : m.Neg_Mu_After,
        absDelta: Math.abs(delta),
      }
    })
}
