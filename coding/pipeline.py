import glob
import os
import random
import pandas as pd
from trueskill import TrueSkill, Rating, rate_1vs1

MU = 25.0
SIGMA = MU / 3

# Canonical team name fixes (wrong -> right)
TEAM_NAME_FIXES = {
    ' - ONLINE': '',
    ' - HYBRID': '',
    'Baylor PM': 'Baylor MP',
    'Harvard SJ': 'Harvard JS',
    'Kansas LH': 'Kansas HL',
    'Kansas PB': 'Kansas BP',
    'Kentucky SR': 'Kentucky RS',
    'UTD RP': 'UTD PR',
    'Western Kentucky NK': 'Western Kentucky KN',
}

# Chronological order of tournaments — controls the final pass ordering.
# Add new tournament codes here in the order they were held.
TOURNAMENT_ORDER = ['nu', 'uk', 'gonzaga', 'wake', 'gt', 'texas', 'ada']

# Elim round sort order (prelim numbers sort before these automatically)
_ELIM_ORDER = {'dubs': 100, 'octas': 101, 'quarters': 102, 'semis': 103, 'finals': 104}


def _round_sort_key(name: str) -> tuple:
    tournament, _, round_label = name.partition('_')
    t_idx = TOURNAMENT_ORDER.index(tournament) if tournament in TOURNAMENT_ORDER else len(TOURNAMENT_ORDER)
    r_idx = int(round_label) if round_label.isdigit() else _ELIM_ORDER.get(round_label, 99)
    return (t_idx, r_idx)


def clean_teams(series: pd.Series) -> pd.Series:
    s = series.copy()
    for wrong, right in TEAM_NAME_FIXES.items():
        s = s.str.replace(wrong, right, regex=False)
    return s


def load_rounds(data_dir: str) -> dict[str, pd.DataFrame]:
    """Auto-discover and load round CSVs from data_dir.

    Only loads files whose tournament prefix is in TOURNAMENT_ORDER — add a
    tournament there to opt it in. Sorted by TOURNAMENT_ORDER then round number
    (prelims before elims).
    """
    files = glob.glob(os.path.join(data_dir, '*.csv'))
    names = sorted(
        [
            os.path.splitext(os.path.basename(f))[0]
            for f in files
            if (
            'entries' not in os.path.basename(f)
            and os.path.splitext(os.path.basename(f))[0].partition('_')[0] in TOURNAMENT_ORDER
        )
        ],
        key=_round_sort_key,
    )
    results = {}
    for name in names:
        df = pd.read_csv(os.path.join(data_dir, f'{name}.csv'))
        df['Aff'] = clean_teams(df['Aff'])
        df['Neg'] = clean_teams(df['Neg'])
        win = df['Win'].str.strip().str.upper()
        df['Win'] = win.map(lambda x: 'Aff' if 'AFF' in x else ('Neg' if 'NEG' in x else x))
        results[name] = df[['Aff', 'Neg', 'Win']]
    return results


def init_teams(data_dir: str) -> pd.DataFrame:
    """Load all *_entries.csv files from data_dir and initialize teams with default ratings."""
    entry_files = glob.glob(os.path.join(data_dir, '*_entries.csv'))
    if not entry_files:
        raise FileNotFoundError(f"No *_entries.csv files found in {data_dir}")
    all_codes = pd.concat(
        [pd.read_csv(f)['Code'] for f in entry_files],
        ignore_index=True,
    )
    teams = clean_teams(all_codes).drop_duplicates().sort_values().reset_index(drop=True)
    return pd.DataFrame({
        'Team': teams,
        'Mu': MU, 'Sigma': SIGMA,
        'Aff_Mu': MU, 'Aff_Sigma': SIGMA,
        'Neg_Mu': MU, 'Neg_Sigma': SIGMA,
        'Aff_Rounds': 0, 'Neg_Rounds': 0,
    })


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

        a = team_idx.loc[aff_name]
        n = team_idx.loc[neg_name]

        r_aff = Rating(a['Mu'], a['Sigma'])
        r_neg = Rating(n['Mu'], n['Sigma'])
        r_aff_side = Rating(a['Aff_Mu'], a['Aff_Sigma'])
        r_neg_side = Rating(n['Neg_Mu'], n['Neg_Sigma'])

        if win == 'Aff':
            new_aff, new_neg = rate_1vs1(r_aff, r_neg, env=env)
            new_aff_side, new_neg_side = rate_1vs1(r_aff_side, r_neg_side, env=env)
            inc = 1
        elif win == 'Neg':
            new_neg, new_aff = rate_1vs1(r_neg, r_aff, env=env)
            new_neg_side, new_aff_side = rate_1vs1(r_neg_side, r_aff_side, env=env)
            inc = 1
        else:
            new_aff, new_neg = r_aff, r_neg
            new_aff_side, new_neg_side = r_aff_side, r_neg_side
            inc = 0

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
    env = env or TrueSkill()
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
    teams = teams.sort_values('Mu', ascending=False).reset_index(drop=True)

    return teams, pd.DataFrame(all_history)
