"""Usage: python run.py [season ...]   (default: current season; 'all' runs every season)"""
import os
import shutil
import sys
from pipeline import CURRENT_SEASON, SEASONS, fit_debaters, load_season, run_pipeline, seed_priors

CODING_DIR = os.path.dirname(__file__)
FRONTEND_DATA = os.path.join(CODING_DIR, '..', 'frontend', 'public', 'data')


def run_season(season: str):
    cfg = SEASONS[season]
    data_dir = os.path.join(CODING_DIR, cfg['data_dir'])
    output_teams = os.path.join(CODING_DIR, cfg['teams_file'])
    output_history = os.path.join(CODING_DIR, cfg['history_file'])

    print(f"Loading {season} data...")
    teams, results, unresolved = load_season(data_dir, cfg['tournaments'], cfg['name_fixes'])
    if unresolved:
        print(f"  {len(unresolved)} code(s) not tied to debaters, rated by code: {', '.join(unresolved)}")

    priors = None
    if (prior_season := cfg.get('prior_season')):
        prior_cfg = SEASONS[prior_season]
        print(f"Seeding from {prior_season}...")
        prior_teams, prior_results, _ = load_season(
            os.path.join(CODING_DIR, prior_cfg['data_dir']),
            prior_cfg['tournaments'], prior_cfg['name_fixes'],
        )
        priors = seed_priors(teams, fit_debaters(prior_teams, prior_results))
        print(f"  {len(priors)} of {len(teams)} teams start from last season's debaters")

    print(f"Rating {len(results)} rounds...")
    final_teams, history = run_pipeline(teams, results, priors=priors)

    final_teams.to_csv(output_teams, index=False)
    history.to_csv(output_history, index=False)

    # Keep frontend data in sync
    os.makedirs(FRONTEND_DATA, exist_ok=True)
    shutil.copy(output_teams, FRONTEND_DATA)
    shutil.copy(output_history, FRONTEND_DATA)

    print(f"\n{len(final_teams)} teams ranked. Top 5:")
    print(final_teams[['Team', 'Mu', 'Conservative']].head().to_string(index=False))


def main():
    seasons = sys.argv[1:] or [CURRENT_SEASON]
    if seasons == ['all']:
        seasons = list(SEASONS)
    unknown = [s for s in seasons if s not in SEASONS]
    if unknown:
        sys.exit(f"Unknown season(s): {', '.join(unknown)}. Choose from: {', '.join(SEASONS)}, all")
    for season in seasons:
        run_season(season)


if __name__ == '__main__':
    main()
