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

function tournamentName(tournament) {
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

async function parseCsv(path) {
  const res = await fetch(path)
  const text = await res.text()
  return Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true }).data
}

const _cache = {}

export async function loadData(season) {
  if (_cache[season]) return _cache[season]
  const base = import.meta.env.BASE_URL
  const { teams: teamsFile, history: historyFile } = SEASONS[season]
  const [teams, rawHistory] = await Promise.all([
    parseCsv(`${base}data/${teamsFile}`),
    parseCsv(`${base}data/${historyFile}`),
  ])
  _cache[season] = { teams, rawHistory }
  return _cache[season]
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
