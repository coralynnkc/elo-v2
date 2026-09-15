# elo-v2

TrueSkill ratings for college policy debate teams, built from Tabroom round results.

**Live site:** https://coralynnkc.github.io/elo-v2/

The site has a sortable leaderboard for each season and a page per team with its round-by-round rating history.

| Season | Topic key | Tournaments |
|---|---|---|
| 2026–27 | `arms` | Northwestern |
| 2025–26 | `labor` | Northwestern, Kentucky RR, Kentucky, Gonzaga, Wake Forest, Georgetown, Dartmouth RR, Texas, ADA, NDT |

## How ratings work

Each team has a TrueSkill rating: a skill estimate **μ** (starting at 25) and an uncertainty **σ** (starting at 25/3). Each round is a 1-vs-1 result that moves the winner up and the loser down. Upsets move ratings more, and so does a large σ.

- **Leaderboard order:** by μ.
- **Conservative score:** μ − 3σ, a lower bound that penalizes teams with few rounds.
- **Eligibility:** a team needs at least 2 tournaments to be ranked. Until a season has 2 tournaments, every team is shown and the site marks the rankings as provisional.

Known limitations and planned methodology changes are tracked in [`planning.md`](planning.md).

## Setup

```bash
pip install pandas trueskill
cd frontend && npm install
```

## Usage

```bash
python coding/run.py            # rate the current season
python coding/run.py labor      # rate a specific season
python coding/run.py all        # rate every season

cd frontend && npm run dev      # http://localhost:5173/elo-v2/
```

`run.py` writes `teams_<season>.csv` and `match_history_<season>.csv` into `coding/`, then copies them to `frontend/public/data/`, which is where the site reads them from.

## Adding a tournament

1. Export the rounds from Tabroom into the season's data folder (for example `coding/data_arms/`):
   - `<code>_entries.csv`: the team list (`Code` and `Entry` columns)
   - `<code>_<round>.csv`: one file per round, with `Aff`, `Neg` and `Win` columns. Rounds are `1`–`8`, then `dubs`, `octas`, `quarters`, `semis`, `finals`.
2. Append `<code>` to `SEASONS[<season>]['tournaments']` in `coding/pipeline.py`. Keep the list in chronological order, because it sets the order rounds are rated in.
3. If the code is new, add a display name to `TOURNAMENT_NAMES` in `frontend/src/utils/data.js`.
4. Run `python coding/run.py`, then commit the data files.

### Team names

Tabroom team codes aren't always consistent, so the pipeline normalizes them:

- **Suffixes:** ` - ONLINE` and ` - HYBRID` are stripped.
- **Reversed initials:** codes that differ only by swapped final initials (`Baylor PM` / `Baylor MP`) are merged. To keep a real pair of different teams apart, add them to `REVERSED_INITIALS_EXCEPTIONS`.
- **Other fixes:** anything else goes in that season's `name_fixes` in `SEASONS`.

## Deploying

Push to `main`. GitHub Actions builds `frontend/` and publishes it to GitHub Pages. The site only shows data that has been committed, so run the pipeline and commit its output before you push.

## Layout

```
coding/
  pipeline.py        loading, name cleanup, TrueSkill updates, season config
  run.py             command-line entry point
  data_<season>/     Tabroom exports
frontend/
  src/utils/data.js  CSV loading, tournament and round display names
  src/pages/         Leaderboard, TeamPage
  public/data/       published ratings (generated)
```
