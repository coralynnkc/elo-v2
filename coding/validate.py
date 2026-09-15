"""Sanity-check a tournament's Tabroom exports before rating it.

Usage: python validate.py [season] [tournament]
       (default: current season, its most recent tournament; 'all' checks every tournament)

Exits 1 if any ERROR is found. WARN lines deserve a look; info lines are expected quirks.
"""
import glob
import os
import re
import sys
import pandas as pd
from pipeline import CURRENT_SEASON, SEASONS, _ELIM_ORDER, load_season

CODING_DIR = os.path.dirname(__file__)
DATA_JS = os.path.join(CODING_DIR, '..', 'frontend', 'src', 'utils', 'data.js')

# Round robins have fixed schedules, so the side and record checks below don't apply
MIN_POWER_MATCHED_FIELD = 16
# Even prelims are side-flipped from the round before, so nearly every team should switch
MIN_EVEN_ROUND_FLIP_RATE = 0.9
# Power-matched prelims pair teams with similar records
MAX_MEAN_RECORD_GAP = 1.5
FIRST_POWER_MATCHED_ROUND = 3


class Report:
    def __init__(self):
        self.errors = 0

    def error(self, msg):
        self.errors += 1
        print(f'  ERROR  {msg}')

    def warn(self, msg):
        print(f'  WARN   {msg}')

    def info(self, msg):
        print(f'  info   {msg}')


def _teams_in(df: pd.DataFrame) -> set:
    return set(df['Aff'].dropna()) | set(df['Neg'].dropna())


def check_config(season: str, tournament: str, report: Report):
    cfg = SEASONS[season]
    data_dir = os.path.join(CODING_DIR, cfg['data_dir'])
    prefixes = {os.path.basename(f).partition('_')[0] for f in glob.glob(os.path.join(data_dir, '*.csv'))}
    for p in sorted(prefixes - set(cfg['tournaments'])):
        report.warn(f"files with prefix '{p}_' are ignored: add it to SEASONS['{season}']['tournaments']")
    if not glob.glob(os.path.join(data_dir, f'{tournament}_entries*.csv')):
        report.warn(f'no {tournament}_entries.csv: debaters can only come from speaker names or other tournaments')
    if os.path.exists(DATA_JS) and not re.search(rf'^\s*{re.escape(tournament)}\s*:', open(DATA_JS).read(), re.M):
        report.warn(f"no TOURNAMENT_NAMES entry for '{tournament}' in frontend/src/utils/data.js")


def check_names(rounds: dict, teams: pd.DataFrame, report: Report):
    played_here = set().union(*(_teams_in(df) for df in rounds.values()))
    debaters = dict(zip(teams['Team'], teams['Debaters']))
    for team in sorted(played_here):
        if not debaters.get(team):
            report.warn(f'{team}: not tied to debaters (no entries or speaker names); rated by its code')
        elif '(' in team:
            report.info(f'{team}: shares its code with another partnership this season')


def check_rows(rounds: dict, report: Report):
    for name, df in rounds.items():
        for row in df[df['Aff'].isna() | df['Neg'].isna()].itertuples():
            report.info(f'{name}: bye for {row.Aff if isinstance(row.Aff, str) else row.Neg}')
        for row in df[~df['Win'].isin(['Aff', 'Neg'])].dropna(subset=['Aff', 'Neg']).itertuples():
            report.info(f'{name}: no debated result ({row.Win}) for {row.Aff} vs {row.Neg}')
        teams = pd.concat([df['Aff'], df['Neg']]).dropna()
        for team in sorted(set(teams[teams.duplicated()])):
            report.error(f'{name}: {team} appears more than once')


def check_prelim_order(tournament: str, rounds: dict, report: Report):
    prelims = sorted(int(n.partition('_')[2]) for n in rounds if n.partition('_')[2].isdigit())
    if not prelims:
        return
    missing = sorted(set(range(1, prelims[-1] + 1)) - set(prelims))
    if missing:
        report.error(f'missing prelim file(s): {", ".join(f"{tournament}_{r}.csv" for r in missing)}')

    field = set().union(*(_teams_in(rounds[f'{tournament}_{r}']) for r in prelims))
    if len(field) < MIN_POWER_MATCHED_FIELD:
        report.info(f'{len(field)}-team field (round robin?): side and power-matching checks skipped')
        return

    wins, side = {}, {}
    print('         round  side-flip  mean record gap')
    for r in prelims:
        df = rounds[f'{tournament}_{r}'].dropna(subset=['Aff', 'Neg'])
        flips = [side[t] != s for t, s in [*((a, 'Aff') for a in df['Aff']), *((n, 'Neg') for n in df['Neg'])] if t in side]
        flip_rate = sum(flips) / len(flips) if flips and r - 1 in prelims else None
        gaps = [abs(wins.get(a, 0) - wins.get(n, 0)) for a, n in zip(df['Aff'], df['Neg'])]
        gap = sum(gaps) / len(gaps) if gaps else 0
        print(f'         {r:>5}  {"" if flip_rate is None else f"{flip_rate:9.0%}":>9}  {gap:15.2f}')

        if flip_rate is not None and r % 2 == 0 and flip_rate < MIN_EVEN_ROUND_FLIP_RATE:
            report.warn(f'round {r}: only {flip_rate:.0%} of teams switched sides; is the file mislabeled or out of order?')
        if r >= FIRST_POWER_MATCHED_ROUND and gap > MAX_MEAN_RECORD_GAP:
            report.warn(f'round {r}: opponents differ by {gap:.2f} wins on average; is the file mislabeled or out of order?')

        side = {**{a: 'Aff' for a in df['Aff']}, **{n: 'Neg' for n in df['Neg']}}
        for row in df.itertuples():
            winner = row.Aff if row.Win == 'Aff' else row.Neg if row.Win == 'Neg' else None
            if winner:
                wins[winner] = wins.get(winner, 0) + 1


def check_bracket(tournament: str, rounds: dict, report: Report):
    elims = [label for label in _ELIM_ORDER if f'{tournament}_{label}' in rounds]
    for prev, cur in zip(elims, elims[1:]):
        p = rounds[f'{tournament}_{prev}'].dropna(subset=['Aff', 'Neg'])
        c = _teams_in(rounds[f'{tournament}_{cur}'])
        winners, losers = set(), set()
        for row in p.itertuples():
            if row.Win in ('Aff', 'Neg'):
                winners.add(row.Aff if row.Win == 'Aff' else row.Neg)
                losers.add(row.Neg if row.Win == 'Aff' else row.Aff)
        for team in sorted(c & losers):
            report.error(f'{cur}: {team} lost in {prev} but debates again')
        for team in sorted(winners - c):
            report.info(f'{cur}: {team} won {prev} but has no {cur} row (closeout or elimination bye in the export)')
        for team in sorted(c - _teams_in(p)):
            report.info(f'{cur}: {team} did not debate {prev} (bye or closeout)')


def check_ballots(season: str, tournament: str, report: Report):
    data_dir = os.path.join(CODING_DIR, SEASONS[season]['data_dir'])
    for label in _ELIM_ORDER:
        path = os.path.join(data_dir, f'{tournament}_{label}.csv')
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        if 'Votes' not in df:
            continue
        for row in df.dropna(subset=['Aff', 'Neg', 'Votes']).itertuples():
            aff = len(re.findall(r'\bAff\b', row.Votes, re.I))
            neg = len(re.findall(r'\bNeg\b', row.Votes, re.I))
            win = str(row.Win).upper()
            called = 'Aff' if 'AFF' in win else 'Neg' if 'NEG' in win else None
            if called and aff != neg and called != ('Aff' if aff > neg else 'Neg'):
                report.error(f'{label}: {row.Aff} vs {row.Neg} ballots {aff}-{neg} Aff but result says {called}')


def validate(season: str, tournament: str) -> int:
    cfg = SEASONS[season]
    data_dir = os.path.join(CODING_DIR, cfg['data_dir'])
    print(f'\n== {season} / {tournament}')
    report = Report()
    check_config(season, tournament, report)

    teams, everything, _ = load_season(data_dir, cfg['tournaments'], cfg['name_fixes'])
    rounds = {n: df for n, df in everything.items() if n.partition('_')[0] == tournament}
    if not rounds:
        report.error(f'no round files for {tournament}')
        return report.errors

    check_names(rounds, teams, report)
    check_rows(rounds, report)
    check_prelim_order(tournament, rounds, report)
    check_bracket(tournament, rounds, report)
    check_ballots(season, tournament, report)
    print(f'  {report.errors} error(s)')
    return report.errors


def main():
    args = sys.argv[1:]
    season = args[0] if args else CURRENT_SEASON
    if season not in SEASONS:
        sys.exit(f"Unknown season '{season}'. Choose from: {', '.join(SEASONS)}")
    tournaments = SEASONS[season]['tournaments']
    chosen = args[1] if len(args) > 1 else tournaments[-1]
    targets = tournaments if chosen == 'all' else [chosen]
    unknown = [t for t in targets if t not in tournaments]
    if unknown:
        sys.exit(f"'{unknown[0]}' is not in SEASONS['{season}']['tournaments']")
    errors = sum(validate(season, t) for t in targets)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
