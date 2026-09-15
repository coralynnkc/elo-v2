"""Usage: python run.py [season ...]   (default: current season; 'all' runs every season)"""
import os
import shutil
import sys
from trueskill import TrueSkill
from pipeline import CURRENT_SEASON, SEASONS, load_season, run_pipeline

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

    print(f"Running pipeline ({len(results)} rounds, 5 passes)...")
    env = TrueSkill(draw_probability=0)  # debate rounds can't be drawn
    final_teams, history = run_pipeline(teams, results, n_passes=5, env=env)

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
