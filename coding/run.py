import os
import shutil
from trueskill import TrueSkill
from pipeline import init_teams, load_rounds, run_pipeline

CODING_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(CODING_DIR, 'data_labor')
OUTPUT_TEAMS = os.path.join(CODING_DIR, 'teams_labor.csv')
OUTPUT_HISTORY = os.path.join(CODING_DIR, 'match_history.csv')
FRONTEND_DATA = os.path.join(CODING_DIR, '..', 'frontend', 'public', 'data')


def main():
    print("Loading data...")
    teams = init_teams(DATA_DIR)
    results = load_rounds(DATA_DIR)

    print(f"Running pipeline ({len(results)} rounds, 5 passes)...")
    env = TrueSkill()
    final_teams, history = run_pipeline(teams, results, n_passes=5, env=env)

    final_teams.to_csv(OUTPUT_TEAMS, index=False)
    history.to_csv(OUTPUT_HISTORY, index=False)

    # Keep frontend data in sync
    os.makedirs(FRONTEND_DATA, exist_ok=True)
    shutil.copy(OUTPUT_TEAMS, FRONTEND_DATA)
    shutil.copy(OUTPUT_HISTORY, FRONTEND_DATA)

    print(f"\n{len(final_teams)} teams ranked. Top 5:")
    print(final_teams[['Team', 'Mu', 'Conservative']].head().to_string(index=False))


if __name__ == '__main__':
    main()
