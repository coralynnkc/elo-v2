"""Walk-forward evaluation of the rating model.

For each tournament k, fit on tournaments 1..k-1 only and predict every decisive round
of tournament k. Nothing the model sees has happened after the round it predicts, so the
scores are honest out-of-sample numbers — unlike the "before" ratings in the old 5-pass
replay, which had already absorbed the results they predicted.

Usage: python evaluate.py [season ...|all] [options]
  --model ttt|forward   rating model (default ttt, the leaderboard's)
  --beta N              performance noise (default 25/6)
  --gamma N             skill drift per tournament (default 25/300)
  --sigma N             prior uncertainty (default 25/3)
  --aff-offset N        skill points added to the aff before predicting (default 0)
  --priors SEASON       seed teams from that season's debater ratings, which makes the
                        first tournament predictable too
  --inflation N         uncertainty added to a seeded team (default 4, needs --priors)
  --sweep beta|gamma|aff-offset|inflation[,...]   scan parameters and print a table
"""
import math
import sys
from statistics import NormalDist
import pandas as pd
from trueskill import TrueSkill, Rating, rate_1vs1
from pipeline import (
    BETA, CURRENT_SEASON, GAMMA, MU, PRIOR_INFLATION, SEASONS, SIGMA,
    fit_debaters, fit_through_time, load_season, seed_priors,
)
import os

CODING_DIR = os.path.dirname(__file__)
_NORMAL = NormalDist()

# Probabilities are clamped before the log, so one upset can't dominate the log loss
EPS = 1e-6

# Values scanned by --sweep, as multiples of the pipeline default (aff-offset is absolute)
SWEEP_GRIDS = {
    'beta': [0.5, 0.75, 1.0, 1.5, 2.0, 3.0],
    'gamma': [0.0, 0.5, 1.0, 2.0, 4.0, 8.0],
    'aff-offset': [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0],
    'inflation': [1.0, 2.0, 4.0, 6.0, 8.0, 12.0],
}


def win_probability(aff, neg, beta: float, aff_offset: float = 0.0) -> float:
    """P(aff wins), given two (mu, sigma) ratings. Both teams' uncertainty and the
    per-round performance noise widen the denominator, so a shaky favourite is
    predicted less confidently than a well-measured one."""
    denom = math.sqrt(2 * beta ** 2 + aff.sigma ** 2 + neg.sigma ** 2)
    return _NORMAL.cdf((aff.mu + aff_offset - neg.mu) / denom)


def decisive_rows(rd: pd.DataFrame):
    """The rows of a round that were actually debated and won by a side."""
    for row in rd.itertuples(index=False):
        if row.Win in ('Aff', 'Neg') and isinstance(row.Aff, str) and isinstance(row.Neg, str):
            yield row


def _tournament(round_name: str) -> str:
    return round_name.partition('_')[0]


def fit_ttt(results, beta: float, gamma: float, sigma: float, priors: dict) -> dict:
    """TTT ratings after the last fitted tournament, drifted one step forward.

    fit_through_time returns each team's rating as of the last tournament it attended;
    gamma is the drift that accrues before the next one, so it is added here. Seeded
    teams that haven't competed yet carry their prior through unchanged.
    """
    seeded = {team: Rating(p.mu, p.sigma) for team, p in priors.items()}
    if not results:
        return seeded
    fit = fit_through_time(results, gamma=gamma, mu=MU, sigma=sigma, beta=beta, priors=priors)
    return seeded | {
        team: Rating(r.mu, math.sqrt(r.sigma ** 2 + gamma ** 2))
        for team, r in fit.items()
    }


def fit_forward(results, beta: float, gamma: float, sigma: float, priors: dict) -> dict:
    """One chronological TrueSkill pass, the model behind the site's match history.

    Like _apply_round, every match in a round is read from the state before that round,
    so pairings within a round don't affect each other.
    """
    env = TrueSkill(mu=MU, sigma=sigma, beta=beta, tau=gamma, draw_probability=0)
    ratings = {team: Rating(p.mu, p.sigma) for team, p in priors.items()}
    for rd in results.values():
        updates = {}
        for row in decisive_rows(rd):
            aff = ratings.get(row.Aff, Rating(MU, sigma))
            neg = ratings.get(row.Neg, Rating(MU, sigma))
            if row.Win == 'Aff':
                updates[row.Aff], updates[row.Neg] = rate_1vs1(aff, neg, env=env)
            else:
                updates[row.Neg], updates[row.Aff] = rate_1vs1(neg, aff, env=env)
        ratings.update(updates)
    return ratings


MODELS = {'ttt': fit_ttt, 'forward': fit_forward}


def walk_forward(
    results: dict[str, pd.DataFrame],
    model: str = 'ttt',
    beta: float = BETA,
    gamma: float = GAMMA,
    sigma: float = SIGMA,
    aff_offset: float = 0.0,
    priors: dict | None = None,
) -> pd.DataFrame:
    """Predict every tournament from the ones before it. One row per decisive match.

    Without priors the first tournament is unpredictable and is skipped; with them it is
    the most interesting one to score, since every team there is a cold start.
    """
    fit_fn = MODELS[model]
    priors = priors or {}
    tournaments = list(dict.fromkeys(_tournament(name) for name in results))

    rows = []
    for k, tournament in enumerate(tournaments):
        if k == 0 and not priors:
            continue  # nothing to fit on
        seen = set(tournaments[:k])
        prefix = {n: rd for n, rd in results.items() if _tournament(n) in seen}
        fit = fit_fn(prefix, beta, gamma, sigma, priors)
        prior = Rating(MU, sigma)

        for name, rd in results.items():
            if _tournament(name) != tournament:
                continue
            label = name.partition('_')[2]
            for row in decisive_rows(rd):
                rows.append({
                    'Tournament': tournament,
                    'Round_Label': label,
                    'Elim': not label.isdigit(),
                    'Aff': row.Aff,
                    'Neg': row.Neg,
                    'Both_Seen': row.Aff in fit and row.Neg in fit,
                    'Seeded_Only': k == 0,
                    'P_Aff': win_probability(
                        fit.get(row.Aff, prior), fit.get(row.Neg, prior), beta, aff_offset
                    ),
                    'Aff_Won': row.Win == 'Aff',
                })
    return pd.DataFrame(rows)


def score(preds: pd.DataFrame) -> dict:
    """Accuracy, log loss and Brier score for a set of predictions."""
    if preds.empty:
        return {'N': 0, 'Accuracy': float('nan'), 'Log_Loss': float('nan'), 'Brier': float('nan')}
    p = preds['P_Aff'].clip(EPS, 1 - EPS)
    y = preds['Aff_Won'].astype(float)
    p_actual = p.where(preds['Aff_Won'], 1 - p)
    return {
        'N': len(preds),
        # A coin-flip prediction is scored as half a win rather than silently as a loss
        'Accuracy': ((p_actual > 0.5) + 0.5 * (p_actual == 0.5)).mean(),
        'Log_Loss': -p_actual.map(math.log).mean(),
        'Brier': ((p - y) ** 2).mean(),
    }


def baselines(preds: pd.DataFrame) -> pd.DataFrame:
    """What the metrics look like without a rating model: a coin flip, and the season's
    own aff win rate (which no forecaster would know in advance)."""
    rows = []
    for label, p in [('coin flip', 0.5), ('aff base rate', preds['Aff_Won'].mean())]:
        flat = preds.assign(P_Aff=p)
        rows.append({'Predictor': label, **score(flat)})
    return pd.DataFrame(rows)


def report(season: str, preds: pd.DataFrame):
    if preds.empty:
        print(f'  no predictable rounds (a season needs at least two tournaments)')
        return

    per_tournament = pd.DataFrame([
        {'Tournament': t, **score(g)} for t, g in preds.groupby('Tournament', sort=False)
    ])
    print('\nBy tournament (fit on everything before it):')
    print(_fmt(per_tournament))

    splits = [
        ('overall', preds),
        ('prelims', preds[~preds['Elim']]),
        ('elims', preds[preds['Elim']]),
        ('both teams rated', preds[preds['Both_Seen']]),
        ('a team unrated', preds[~preds['Both_Seen']]),
    ]
    if preds['Seeded_Only'].any():
        splits.insert(1, ('first tournament (seeded only)', preds[preds['Seeded_Only']]))
    print('\nSplits:')
    print(_fmt(pd.DataFrame([{'Split': label, **score(g)} for label, g in splits])))

    print('\nBaselines:')
    print(_fmt(baselines(preds)))


def _fmt(df: pd.DataFrame) -> str:
    return df.to_string(index=False, float_format=lambda v: f'{v:.4f}')


def sweep(results, parameters: list[str], reseed=None, **kwargs) -> pd.DataFrame:
    """Rescore the season once per value of each swept parameter, holding the rest fixed.

    beta and gamma are scanned as multiples of the pipeline default; aff-offset and
    inflation are absolute, since their default of 0 / 4 has no useful multiples.
    """
    defaults = {'beta': BETA, 'gamma': GAMMA, 'aff-offset': 0.0, 'inflation': PRIOR_INFLATION}
    absolute = {'aff-offset', 'inflation'}
    rows = []
    for parameter in parameters:
        base = defaults[parameter]
        for step in SWEEP_GRIDS[parameter]:
            value = step if parameter in absolute else base * step
            if parameter == 'inflation':
                if reseed is None:
                    sys.exit('--sweep inflation needs --priors')
                settings = {**kwargs, 'priors': reseed(value)}
            else:
                settings = {**kwargs, parameter.replace('-', '_'): value}
            rows.append({
                'Parameter': parameter,
                'Value': value,
                'Default': abs(value - base) < 1e-12,
                **score(walk_forward(results, **settings)),
            })
    return pd.DataFrame(rows)


def parse_args(argv: list[str]) -> tuple[list[str], dict, list[str]]:
    seasons, options, swept = [], {}, []
    floats = {'--beta': 'beta', '--gamma': 'gamma', '--sigma': 'sigma',
              '--aff-offset': 'aff_offset', '--inflation': 'inflation'}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '--sweep':
            swept = argv[i + 1].split(',')
            i += 2
        elif arg in ('--model', '--priors'):
            options[arg[2:]] = argv[i + 1]
            i += 2
        elif arg in floats:
            options[floats[arg]] = float(argv[i + 1])
            i += 2
        elif arg.startswith('--'):
            sys.exit(f'Unknown option: {arg}\n{__doc__}')
        else:
            seasons.append(arg)
            i += 1

    if seasons == ['all']:
        seasons = list(SEASONS)
    seasons = seasons or [CURRENT_SEASON]
    if unknown := [s for s in seasons if s not in SEASONS]:
        sys.exit(f"Unknown season(s): {', '.join(unknown)}. Choose from: {', '.join(SEASONS)}, all")
    if options.get('model', 'ttt') not in MODELS:
        sys.exit(f"Unknown model: {options['model']}. Choose from: {', '.join(MODELS)}")
    if (prior_season := options.get('priors')) and prior_season not in SEASONS:
        sys.exit(f"Unknown priors season: {prior_season}. Choose from: {', '.join(SEASONS)}")
    if 'inflation' in options and 'priors' not in options:
        sys.exit('--inflation has no effect without --priors')
    if unknown := [p for p in swept if p not in SWEEP_GRIDS]:
        sys.exit(f"Can't sweep {', '.join(unknown)}. Choose from: {', '.join(SWEEP_GRIDS)}")
    return seasons, options, swept


def _load(season: str):
    cfg = SEASONS[season]
    return load_season(
        os.path.join(CODING_DIR, cfg['data_dir']), cfg['tournaments'], cfg['name_fixes']
    )


def main():
    seasons, options, swept = parse_args(sys.argv[1:])
    prior_season = options.pop('priors', None)
    inflation = options.pop('inflation', PRIOR_INFLATION)

    for season in seasons:
        teams, results, _ = _load(season)
        settings = {'model': 'ttt', 'beta': BETA, 'gamma': GAMMA, 'sigma': SIGMA, 'aff_offset': 0.0}
        settings.update(options)

        reseed = None
        if prior_season:
            if prior_season == season:
                sys.exit(f"Can't seed {season} from itself")
            debaters = fit_debaters(*_load(prior_season)[:2])
            reseed = lambda n, t=teams, d=debaters: seed_priors(t, d, n)
            settings['priors'] = reseed(inflation)
            print(f'\n  seeded {len(settings["priors"])} of {len(teams)} {season} teams '
                  f'from {len(debaters)} {prior_season} debaters (inflation {inflation})')

        print(f"\n=== {season} ({len(results)} rounds) ===")
        print('  ' + '  '.join(f'{k}={v:.4f}' if isinstance(v, float) else f'{k}={len(v)} teams'
                               if k == 'priors' else f'{k}={v}' for k, v in settings.items()))
        if swept:
            print(_fmt(sweep(results, swept, reseed=reseed, **settings)))
        else:
            report(season, walk_forward(results, **settings))


if __name__ == '__main__':
    main()
