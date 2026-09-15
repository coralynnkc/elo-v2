import glob
import os
import random
from functools import partial
import pandas as pd
from trueskill import TrueSkill, Rating, rate_1vs1

MU = 25.0
SIGMA = MU / 3

# Tabroom suffixes stripped from team codes in every season
SUFFIX_FIXES = {
    ' - ONLINE': '',
    ' - HYBRID': '',
}

# These reversed-initials pairs refer to genuinely different teams — do not collapse
REVERSED_INITIALS_EXCEPTIONS = frozenset({'Kansas BP', 'Kansas PB'})

# Per-season config.
#   tournaments:       chronological order of tournament codes — controls round ordering.
#                      Add new codes here in the order they were held; files with other
#                      prefixes are ignored.
#   name_fixes:        non-reversed-initials name fixes (wrong -> right) for that season only.
#   teams_from_rounds: also rate teams that debated but are missing from the entries lists,
#                      instead of silently dropping their rounds.
SEASONS = {
    'labor': {
        'data_dir': 'data_labor',
        'tournaments': ['nu', 'kentuckyrr', 'uk', 'gonzaga', 'wake', 'gt', 'dartmouthrr', 'texas', 'ada', 'ndt'],
        'name_fixes': {
            'Houston MH': 'Houston HM',
            'Macalester HK': 'Macalester KH',
            'Southern California MB': 'Southern California BM',
            'Wichita State MG': 'Wichita State GM',
        },
        'teams_from_rounds': False,
        'teams_file': 'teams_labor.csv',
        'history_file': 'match_history.csv',
    },
    'arms': {
        'data_dir': 'data_arms',
        'tournaments': ['nu'],
        'name_fixes': {},
        'teams_from_rounds': True,
        'teams_file': 'teams_arms.csv',
        'history_file': 'match_history_arms.csv',
    },
}

CURRENT_SEASON = 'arms'

# Elim round sort order (prelim numbers sort before these automatically)
_ELIM_ORDER = {'dubs': 100, 'octas': 101, 'quarters': 102, 'semis': 103, 'finals': 104}

# Teams must appear in this many tournaments to be ranked (capped at the number loaded)
MIN_TOURNAMENTS = 2


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


def build_reversed_initials_fixes(names) -> dict[str, str]:
    """Find all pairs of team names that differ only by swapped last-two initials
    (e.g. 'Baylor PM' / 'Baylor MP') and return a mapping from the
    alphabetically-later form to the earlier (canonical) form.

    Pairs listed in REVERSED_INITIALS_EXCEPTIONS are left alone.
    """
    fixes = {}
    seen = {}  # name -> canonical name
    for item in sorted(set(names)):
        reversed_item = item[:-2] + item[-2:][::-1]
        if item in REVERSED_INITIALS_EXCEPTIONS or reversed_item in REVERSED_INITIALS_EXCEPTIONS:
            continue
        if reversed_item in seen or item in seen:
            canonical = seen.get(reversed_item) or seen.get(item)
            fixes[item] = canonical
        else:
            seen[item] = item
            seen[reversed_item] = item
    return fixes


def clean_teams(series: pd.Series, *fixes: dict | None) -> pd.Series:
    """Strip Tabroom suffixes, then apply each fixes dict (wrong -> right) in order."""
    s = series.copy()
    for fix in (SUFFIX_FIXES, *fixes):
        for wrong, right in (fix or {}).items():
            s = s.str.replace(wrong, right, regex=False)
    return s


def load_rounds(
    data_dir: str,
    tournament_order: list[str],
    name_fixes: dict | None = None,
    extra_fixes: dict | None = None,
) -> dict[str, pd.DataFrame]:
    """Auto-discover and load round CSVs from data_dir.

    Only loads files whose tournament prefix is in tournament_order. Sorted by
    tournament_order then round number (prelims before elims).
    """
    results = {}
    for name in _round_names(data_dir, tournament_order):
        df = pd.read_csv(os.path.join(data_dir, f'{name}.csv'))
        df['Aff'] = clean_teams(df['Aff'], name_fixes, extra_fixes)
        df['Neg'] = clean_teams(df['Neg'], name_fixes, extra_fixes)
        win = df['Win'].str.strip().str.upper()
        df['Win'] = win.map(lambda x: 'Aff' if 'AFF' in x else ('Neg' if 'NEG' in x else x))
        results[name] = df[['Aff', 'Neg', 'Win']]
    return results


def init_teams(
    data_dir: str,
    tournament_order: list[str],
    name_fixes: dict | None = None,
    teams_from_rounds: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Load all *_entries.csv files from data_dir and initialize teams with default ratings.

    With teams_from_rounds, teams that appear in round CSVs but not in any entries
    list are added too.

    Returns (teams_df, reversed_initials_fixes) so the caller can pass the same
    fixes to load_rounds, ensuring round CSVs use the same canonical names.
    """
    entry_files = glob.glob(os.path.join(data_dir, '*_entries.csv'))
    if not entry_files:
        raise FileNotFoundError(f"No *_entries.csv files found in {data_dir}")
    codes = [pd.read_csv(f)['Code'] for f in entry_files]
    if teams_from_rounds:
        for name in _round_names(data_dir, tournament_order):
            df = pd.read_csv(os.path.join(data_dir, f'{name}.csv'))
            codes += [df['Aff'].dropna(), df['Neg'].dropna()]
    all_codes = pd.concat(codes, ignore_index=True)
    base_cleaned = clean_teams(all_codes, name_fixes)
    rev_fixes = build_reversed_initials_fixes(base_cleaned)
    teams = clean_teams(base_cleaned, rev_fixes).drop_duplicates().sort_values().reset_index(drop=True)
    return pd.DataFrame({
        'Team': teams,
        'Mu': MU, 'Sigma': SIGMA,
        'Aff_Mu': MU, 'Aff_Sigma': SIGMA,
        'Neg_Mu': MU, 'Neg_Sigma': SIGMA,
        'Aff_Rounds': 0, 'Neg_Rounds': 0,
    }), rev_fixes


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


def run_pipeline(
    teams: pd.DataFrame,
    results: dict[str, pd.DataFrame],
    n_passes: int = 5,
    env: TrueSkill = None,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run TrueSkill rating pipeline.

    Passes 1..n-1: shuffle round order to reduce order-dependent bias in warm-up.
    Final pass: chronological order, tracking match history for the frontend.

    Returns (teams_df, match_history_df).
    """
    env = env or TrueSkill(draw_probability=0)
    rng = random.Random(seed)
    round_names = list(results.keys())

    for _ in range(n_passes - 1):
        order = round_names[:]
        rng.shuffle(order)
        for name in order:
            teams, _ = _apply_round(teams, results[name], env)

    # Reset round counts — only the final chronological pass should count them
    teams['Aff_Rounds'] = 0
    teams['Neg_Rounds'] = 0

    all_history = []
    for name in round_names:
        teams, history = _apply_round(teams, results[name], env, track_history=True, round_name=name)
        all_history.extend(history)

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
