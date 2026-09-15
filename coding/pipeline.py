import glob
import os
import re
import unicodedata
from collections import Counter, defaultdict
from functools import partial
import pandas as pd
import trueskillthroughtime as ttt
from trueskill import TrueSkill, Rating, rate_1vs1

MU = 25.0
SIGMA = MU / 3
BETA = SIGMA / 2    # TrueSkill default: performance noise per round
GAMMA = SIGMA / 100  # TrueSkill's default tau, applied here once per tournament

# TrueSkill Through Time convergence
TTT_ITERATIONS = 100
TTT_EPSILON = 1e-4

# Tabroom suffixes stripped from team codes in every season
SUFFIX_FIXES = {
    ' - ONLINE': '',
    ' - HYBRID': '',
}

# Per-season config.
#   tournaments: chronological order of tournament codes — controls round ordering.
#                Add new codes here in the order they were held; files with other
#                prefixes are ignored.
#   name_fixes:  code fixes (wrong -> right) for that season only. Only needed when a code
#                can't be tied to its debaters (no speaker names or entries) and differs
#                from the code used elsewhere.
SEASONS = {
    'labor': {
        'data_dir': 'data_labor',
        'tournaments': ['nu', 'kentuckyrr', 'uk', 'gonzaga', 'wake', 'gt', 'dartmouthrr', 'texas', 'ada', 'ndt'],
        'name_fixes': {
            'Emory CrTa': 'Emory CT',  # Northwestern code for Cross & Taylor
            'Houston MH': 'Houston HM',
            'Macalester HK': 'Macalester KH',
            'Southern California MB': 'Southern California BM',
            'Wichita State MG': 'Wichita State GM',
        },
        'teams_file': 'teams_labor.csv',
        'history_file': 'match_history.csv',
    },
    'arms': {
        'data_dir': 'data_arms',
        'tournaments': ['nu'],
        'name_fixes': {},
        'teams_file': 'teams_arms.csv',
        'history_file': 'match_history_arms.csv',
    },
}

CURRENT_SEASON = 'arms'

# Elim round sort order (prelim numbers sort before these automatically)
_ELIM_ORDER = {'dubs': 100, 'octas': 101, 'quarters': 102, 'semis': 103, 'finals': 104}

# Teams must appear in this many tournaments to be ranked (capped at the number loaded)
MIN_TOURNAMENTS = 2

# One speaker in a points cell: "JGonzalez Arce 28.7" (several scores when judged by a panel)
_SPEAKER = re.compile(r'([^\d\s][^\d]*?)\s+(?:\d+(?:\.\d+)?\s*)+')


def _round_sort_key(name: str, tournament_order: list[str]) -> tuple:
    tournament, _, round_label = name.partition('_')
    t_idx = tournament_order.index(tournament) if tournament in tournament_order else len(tournament_order)
    r_idx = int(round_label) if round_label.isdigit() else _ELIM_ORDER.get(round_label, 99)
    return (t_idx, r_idx)


def _round_names(data_dir: str, tournament_order: list[str]) -> list[str]:
    """Round CSV basenames (no extension) in data_dir whose tournament prefix is in
    tournament_order, sorted chronologically (prelims before elims)."""
    names = [os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(data_dir, '*.csv'))]
    return sorted(
        [n for n in names if 'entries' not in n and n.partition('_')[0] in tournament_order],
        key=partial(_round_sort_key, tournament_order=tournament_order),
    )


def clean_teams(series: pd.Series, *fixes: dict | None) -> pd.Series:
    """Strip Tabroom suffixes, then apply each fixes dict (wrong -> right) in order."""
    s = series.copy()
    for fix in (SUFFIX_FIXES, *fixes):
        for wrong, right in (fix or {}).items():
            s = s.str.replace(wrong, right, regex=False)
    return s


def _normalize_surname(name: str) -> str:
    ascii_name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z]', '', ascii_name.casefold())


def _partnership_key(surnames: list[str]) -> str:
    """Order-, case-, accent- and punctuation-insensitive key for a set of debaters."""
    return '/'.join(sorted(_normalize_surname(s) for s in surnames))


def _entry_surnames(entry) -> list[str] | None:
    """'Gallagher & Young' -> ['Gallagher', 'Young']"""
    if pd.isna(entry):
        return None
    names = [n.strip() for n in str(entry).split('&') if n.strip()]
    return names if len(names) == 2 else None


def _speaker_surnames(cell) -> list[str] | None:
    """'AHant 28.6 JGonzalez Arce 28.7' -> ['Hant', 'Gonzalez Arce']. Names are Tabroom's
    first initial + surname. None unless exactly two speakers are listed (mavericks fall
    back to the team code)."""
    if pd.isna(cell):
        return None
    names = [m.group(1).strip() for m in _SPEAKER.finditer(re.sub(r'\s+', ' ', str(cell)))]
    return [n[1:] for n in names] if len(names) == 2 else None


def _initials_signature(code: str) -> str:
    """'Baylor PM' and 'Baylor MP' share a signature."""
    school, _, initials = code.rpartition(' ')
    return f"{school} {''.join(sorted(initials))}"


def load_season(
    data_dir: str,
    tournament_order: list[str],
    name_fixes: dict | None = None,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], list[str]]:
    """Load a season's round CSVs and identify each team as a debater partnership.

    Each side of each round is resolved, in order, from:
      1. that tournament's entries file (Code -> Entry),
      2. the speaker names in that row's points column (Tabroom shortens these, so entries win),
      3. the partnership seen under that code at the nearest tournament that has one,
      4. the same, matching the code's initials in either order.
    Anything still unresolved is keyed by its code.

    Teams are displayed by their most-used code; when partnerships share one, their
    surnames are appended ('Kansas BP (Bauman/Persson)').

    Returns (teams_df, results, unresolved_codes). results maps round name to a
    DataFrame of Aff, Neg (display names) and Win.
    """
    entries = defaultdict(dict)  # tournament -> code -> surnames
    for tournament in tournament_order:
        for f in sorted(glob.glob(os.path.join(data_dir, f'{tournament}_entries*.csv'))):
            e = pd.read_csv(f)
            for code, entry in zip(clean_teams(e['Code'], name_fixes), e['Entry']):
                if (surnames := _entry_surnames(entry)):
                    entries[tournament][code] = surnames

    rounds = {}
    for name in _round_names(data_dir, tournament_order):
        df = pd.read_csv(os.path.join(data_dir, f'{name}.csv'))
        out = pd.DataFrame(index=df.index)
        for side in ('Aff', 'Neg'):
            out[side] = clean_teams(df[side], name_fixes)
            points = next((c for c in df.columns if c.startswith(side) and 'Points' in c), None)
            out[f'{side}_Speakers'] = df[points].map(_speaker_surnames) if points else None
        win = df['Win'].astype(str).str.strip().str.upper()
        out['Win'] = win.map(lambda x: 'Aff' if 'AFF' in x else ('Neg' if 'NEG' in x else x))
        rounds[name] = out

    # Where each partnership appeared under each code / initials signature this season
    surnames_by_key = {}
    by_code = defaultdict(lambda: defaultdict(set))       # code -> key -> tournament indices
    by_signature = defaultdict(lambda: defaultdict(set))  # signature -> key -> tournament indices

    def observe(code, surnames, tournament):
        key = _partnership_key(surnames)
        surnames_by_key.setdefault(key, surnames)
        t_idx = tournament_order.index(tournament)
        by_code[code][key].add(t_idx)
        by_signature[_initials_signature(code)][key].add(t_idx)

    for tournament, code_map in entries.items():
        for code, surnames in code_map.items():
            observe(code, surnames, tournament)
    # Speaker names fill in where entries are missing; entries win when both exist, since
    # Tabroom speaker names can be shortened ("JSay" for Sayoto)
    for name, df in rounds.items():
        tournament = name.partition('_')[0]
        for side in ('Aff', 'Neg'):
            for code, surnames in zip(df[side], df[f'{side}_Speakers']):
                if isinstance(code, str) and surnames and code not in entries[tournament]:
                    observe(code, surnames, tournament)

    def nearest(candidates: dict, tournament: str) -> str | None:
        """The partnership seen closest in time under this code, if exactly one is."""
        t_idx = tournament_order.index(tournament)
        distance = {key: min(abs(i - t_idx) for i in idxs) for key, idxs in candidates.items()}
        if not distance:
            return None
        closest = min(distance.values())
        keys = [key for key, d in distance.items() if d == closest]
        return keys[0] if len(keys) == 1 else None

    unresolved = set()

    def resolve(code, surnames, tournament):
        if not isinstance(code, str):
            return None  # bye
        if code in entries[tournament]:
            return _partnership_key(entries[tournament][code])
        if surnames:
            return _partnership_key(surnames)
        key = nearest(by_code[code], tournament) or nearest(by_signature[_initials_signature(code)], tournament)
        if key:
            return key
        unresolved.add(code)
        return f'code:{code}'

    tournaments_by_code = defaultdict(lambda: defaultdict(set))  # key -> code -> tournaments
    for name, df in rounds.items():
        tournament = name.partition('_')[0]
        for side in ('Aff', 'Neg'):
            keys = [resolve(c, s, tournament) for c, s in zip(df[side], df[f'{side}_Speakers'])]
            for key, code in zip(keys, df[side]):
                if key:
                    tournaments_by_code[key][code].add(tournament_order.index(tournament))
            df[f'{side}_Key'] = keys

    # Display name: the initials ordering-group used at the most tournaments (ties: most
    # recent), shown in its alphabetically first ordering so names stay stable
    display = {}
    for key, codes in tournaments_by_code.items():
        groups = defaultdict(set)
        for code, idxs in codes.items():
            groups[_initials_signature(code)] |= idxs
        best = max(groups, key=lambda sig: (len(groups[sig]), max(groups[sig])))
        display[key] = min(code for code in codes if _initials_signature(code) == best)
    shared = Counter(display.values())
    for key, code in display.items():
        if shared[code] > 1:
            label = '/'.join(surnames_by_key[key]) if key in surnames_by_key else 'unidentified'
            display[key] = f'{code} ({label})'

    results = {}
    for name, df in rounds.items():
        results[name] = pd.DataFrame({
            'Aff': df['Aff_Key'].map(display),
            'Neg': df['Neg_Key'].map(display),
            'Win': df['Win'],
        })

    keys = sorted(display, key=display.get)
    teams = pd.DataFrame({
        'Team': [display[k] for k in keys],
        'Debaters': [' & '.join(surnames_by_key[k]) if k in surnames_by_key else '' for k in keys],
        'Mu': MU, 'Sigma': SIGMA,
        'Aff_Mu': MU, 'Aff_Sigma': SIGMA,
        'Neg_Mu': MU, 'Neg_Sigma': SIGMA,
        'Aff_Rounds': 0, 'Neg_Rounds': 0,
    })
    return teams, results, sorted(unresolved)


def _apply_round(
    teams: pd.DataFrame,
    rd: pd.DataFrame,
    env: TrueSkill,
    track_history: bool = False,
    round_name: str = '',
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Apply TrueSkill updates for one round.

    All match ratings are read from the BEFORE state so matches within a round
    don't affect each other. Updates are merged back after all rows are processed.
    """
    team_idx = teams.set_index('Team')
    out_aff, out_neg, history = [], [], []

    for row in rd.itertuples(index=False):
        aff_name, neg_name, win = row.Aff, row.Neg, row.Win

        if aff_name not in team_idx.index or neg_name not in team_idx.index:
            continue

        # Skip rows with no debated result, e.g. closeouts ("EMORY GS ADVANCES") and byes
        if win not in ('Aff', 'Neg'):
            continue

        a = team_idx.loc[aff_name]
        n = team_idx.loc[neg_name]

        r_aff = Rating(a['Mu'], a['Sigma'])
        r_neg = Rating(n['Mu'], n['Sigma'])
        r_aff_side = Rating(a['Aff_Mu'], a['Aff_Sigma'])
        r_neg_side = Rating(n['Neg_Mu'], n['Neg_Sigma'])

        if win == 'Aff':
            new_aff, new_neg = rate_1vs1(r_aff, r_neg, env=env)
            new_aff_side, new_neg_side = rate_1vs1(r_aff_side, r_neg_side, env=env)
        else:
            new_neg, new_aff = rate_1vs1(r_neg, r_aff, env=env)
            new_neg_side, new_aff_side = rate_1vs1(r_neg_side, r_aff_side, env=env)
        inc = 1

        out_aff.append({
            'Team': aff_name,
            'New_Mu': new_aff.mu, 'New_Sigma': new_aff.sigma,
            'New_Aff_Mu': new_aff_side.mu, 'New_Aff_Sigma': new_aff_side.sigma,
            'Inc': inc,
        })
        out_neg.append({
            'Team': neg_name,
            'New_Mu': new_neg.mu, 'New_Sigma': new_neg.sigma,
            'New_Neg_Mu': new_neg_side.mu, 'New_Neg_Sigma': new_neg_side.sigma,
            'Inc': inc,
        })

        if track_history:
            tournament, _, round_label = round_name.partition('_')
            history.append({
                'Round': round_name,
                'Tournament': tournament,
                'Round_Label': round_label,
                'Aff': aff_name,
                'Neg': neg_name,
                'Win': win,
                'Aff_Mu_Before': round(a['Mu'], 3),
                'Aff_Mu_After': round(new_aff.mu, 3),
                'Aff_Mu_Delta': round(new_aff.mu - a['Mu'], 3),
                'Neg_Mu_Before': round(n['Mu'], 3),
                'Neg_Mu_After': round(new_neg.mu, 3),
                'Neg_Mu_Delta': round(new_neg.mu - n['Mu'], 3),
            })

    # Apply all updates from the before-state (no intra-round dependency)
    t = teams.copy()

    if out_aff:
        aff_df = pd.DataFrame(out_aff).drop_duplicates(subset='Team', keep='last').set_index('Team')
        mask = t['Team'].isin(aff_df.index)
        t.loc[mask, 'Mu'] = t.loc[mask, 'Team'].map(aff_df['New_Mu'])
        t.loc[mask, 'Sigma'] = t.loc[mask, 'Team'].map(aff_df['New_Sigma'])
        t.loc[mask, 'Aff_Mu'] = t.loc[mask, 'Team'].map(aff_df['New_Aff_Mu'])
        t.loc[mask, 'Aff_Sigma'] = t.loc[mask, 'Team'].map(aff_df['New_Aff_Sigma'])
        t.loc[mask, 'Aff_Rounds'] += t.loc[mask, 'Team'].map(aff_df['Inc']).fillna(0).astype(int)

    if out_neg:
        neg_df = pd.DataFrame(out_neg).drop_duplicates(subset='Team', keep='last').set_index('Team')
        mask = t['Team'].isin(neg_df.index)
        t.loc[mask, 'Mu'] = t.loc[mask, 'Team'].map(neg_df['New_Mu'])
        t.loc[mask, 'Sigma'] = t.loc[mask, 'Team'].map(neg_df['New_Sigma'])
        t.loc[mask, 'Neg_Mu'] = t.loc[mask, 'Team'].map(neg_df['New_Neg_Mu'])
        t.loc[mask, 'Neg_Sigma'] = t.loc[mask, 'Team'].map(neg_df['New_Neg_Sigma'])
        t.loc[mask, 'Neg_Rounds'] += t.loc[mask, 'Team'].map(neg_df['Inc']).fillna(0).astype(int)

    return t, history


def fit_through_time(
    results: dict[str, pd.DataFrame],
    gamma: float = GAMMA,
) -> dict[str, ttt.Gaussian]:
    """Fit TrueSkill Through Time over a season, one time step per tournament.

    Every rating is smoothed over all results, before and after, so it doesn't depend
    on round order and its uncertainty isn't shrunk by replaying results.

    Returns each team's rating as of the last tournament it attended.
    """
    tournaments = list(dict.fromkeys(name.partition('_')[0] for name in results))
    composition, outcomes, times = [], [], []
    for name, rd in results.items():
        t_idx = tournaments.index(name.partition('_')[0])
        for row in rd.itertuples(index=False):
            if row.Win in ('Aff', 'Neg') and isinstance(row.Aff, str) and isinstance(row.Neg, str):
                composition.append([[row.Aff], [row.Neg]])
                outcomes.append([1, 0] if row.Win == 'Aff' else [0, 1])  # higher score wins
                times.append(t_idx)

    history = ttt.History(composition, outcomes, times, mu=MU, sigma=SIGMA, beta=BETA, gamma=gamma)
    history.convergence(epsilon=TTT_EPSILON, iterations=TTT_ITERATIONS, verbose=False)
    return {team: curve[-1][1] for team, curve in history.learning_curves().items()}


def run_pipeline(
    teams: pd.DataFrame,
    results: dict[str, pd.DataFrame],
    env: TrueSkill = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Rate a season.

    Match history (and round counts, side ratings): one forward chronological TrueSkill
    pass, so each round's before/after uses only earlier results.
    Leaderboard Mu/Sigma: TrueSkill Through Time over the whole season.

    Returns (teams_df, match_history_df).
    """
    env = env or TrueSkill(mu=MU, sigma=SIGMA, beta=BETA, tau=GAMMA, draw_probability=0)

    all_history = []
    for name in results:
        teams, history = _apply_round(teams, results[name], env, track_history=True, round_name=name)
        all_history.extend(history)

    fit = fit_through_time(results)
    teams['Mu'] = teams['Team'].map(lambda t: fit[t].mu if t in fit else MU)
    teams['Sigma'] = teams['Team'].map(lambda t: fit[t].sigma if t in fit else SIGMA)
    teams['Conservative'] = teams['Mu'] - 3 * teams['Sigma']
    round_cols = ['Mu', 'Sigma', 'Aff_Mu', 'Aff_Sigma', 'Neg_Mu', 'Neg_Sigma', 'Conservative']
    teams[round_cols] = teams[round_cols].round(3)
    teams = teams[(teams['Aff_Rounds'] > 0) | (teams['Neg_Rounds'] > 0)]

    # Exclude teams that competed in fewer than MIN_TOURNAMENTS tournaments
    # (relaxed early in a season, before that many tournaments exist)
    history_df = pd.DataFrame(all_history)
    if not history_df.empty:
        aff_tours = history_df[['Aff', 'Tournament']].rename(columns={'Aff': 'Team'})
        neg_tours = history_df[['Neg', 'Tournament']].rename(columns={'Neg': 'Team'})
        team_tour_counts = (
            pd.concat([aff_tours, neg_tours])
            .drop_duplicates()
            .groupby('Team')['Tournament']
            .nunique()
        )
        min_tournaments = min(MIN_TOURNAMENTS, history_df['Tournament'].nunique())
        eligible = team_tour_counts[team_tour_counts >= min_tournaments].index
        teams = teams[teams['Team'].isin(eligible)]

    teams = teams.sort_values('Mu', ascending=False).reset_index(drop=True)

    return teams, pd.DataFrame(all_history)
