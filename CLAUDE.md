# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A TrueSkill rating system for academic Policy debate tournaments. Tracks team performance across multiple tournaments and produces a final leaderboard with skill ratings.

## Running the Pipeline

```bash
cd coding
conda run -n base python run.py   # or: python run.py if deps are active
```

Outputs `teams_labor.csv` (rankings) and `match_history.csv` (per-match deltas for the frontend).

The original `trueskill.ipynb` notebook is kept for exploratory/validation work.

## Architecture

Two source files in `coding/`:

- **`pipeline.py`** — all core logic: `init_teams`, `load_rounds`, `_apply_round`, `run_pipeline`
- **`run.py`** — thin entry point; imports from `pipeline.py` and writes CSV outputs

The pipeline runs in three phases:

1. **Init** — Load `gt_entries.csv`, normalize team names (`TEAM_NAME_FIXES`), assign default TrueSkill ratings (Mu=25.0, Sigma=25/3)
2. **Warm-up passes (n-1 times)** — Shuffle round order each pass and apply TrueSkill updates; this averages out order-dependent bias without re-counting rounds
3. **Final pass (chronological)** — Reset round counts to zero, run once in tournament order, track per-match Mu deltas into `match_history.csv`

## Data Layout

- `coding/data_labor/{tournament}_{round}.csv` — Raw round results (62 files). Columns: `Aff`, `Neg`, `Win` (values: `Aff` or `Neg`)
- `coding/gt_entries.csv` — Tournament entry metadata; `Code` column is the canonical team name source
- `coding/teams_labor.csv` — Final output: per-team `Mu`, `Sigma`, `Aff_Mu`, `Aff_Sigma`, `Neg_Mu`, `Neg_Sigma`, `Aff_Rounds`, `Neg_Rounds`, `Conservative`
- `coding/match_history.csv` — Per-match records: `Round`, `Tournament`, `Round_Label`, `Aff`, `Neg`, `Win`, `Aff_Mu_Before/After/Delta`, `Neg_Mu_Before/After/Delta`

Tournaments: NU (Northwestern), UK (Kentucky), Gonzaga, Wake (Wake Forest), GT (Georgia Tech).

## Key Implementation Details

- **Intra-round independence**: `_apply_round` reads all ratings from the pre-round state and applies all updates at the end, so matches within a round don't affect each other
- **Side-specific ratings**: Aff/Neg skill tracked independently alongside overall Mu/Sigma
- **Team name normalization**: `TEAM_NAME_FIXES` in `pipeline.py` is the single source of truth — add new fixes there
- **`Aff_Mu_Delta` / `Neg_Mu_Delta`** in match history represent how much each team's rating moved in that match; sort by `abs(delta)` to find "most consequential" rounds per team
