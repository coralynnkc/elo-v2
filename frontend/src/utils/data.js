import Papa from 'papaparse'

const TOURNAMENT_NAMES = {
  nu: 'Northwestern',
  uk: 'Kentucky',
  gonzaga: 'Gonzaga',
  wake: 'Wake Forest',
  gt: 'Georgetown',
  texas: 'Texas',
  ada: 'ADA',
}

const ELIM_LABELS = {
  dubs: 'Doubles',
  octas: 'Octafinals',
  quarters: 'Quarterfinals',
  semis: 'Semifinals',
  finals: 'Finals',
}

export function formatRound(tournament, roundLabel) {
  const t = TOURNAMENT_NAMES[tournament] || tournament.toUpperCase()
  const r = isNaN(Number(roundLabel))
    ? (ELIM_LABELS[roundLabel] || roundLabel)
    : `R${roundLabel}`
  return `${t} ${r}`
}

async function parseCsv(path) {
  const res = await fetch(path)
  const text = await res.text()
  return Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true }).data
}

let _cache = null

export async function loadData() {
  if (_cache) return _cache
  const [teams, rawHistory] = await Promise.all([
    parseCsv('/data/teams_labor.csv'),
    parseCsv('/data/match_history.csv'),
  ])
  _cache = { teams, rawHistory }
  return _cache
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
