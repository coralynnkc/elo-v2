# Planning: methodology improvements

Open work on the rating pipeline (`coding/pipeline.py`), in priority order. Data-entry steps are in README.md.

## Decisions so far
- **Rating model:** TrueSkill Through Time (TTT) for leaderboard ratings. Match history comes from one forward chronological pass. See #1.
- **Draws:** `draw_probability=0`. Debate rounds can't be drawn.
- **Non-decisive rows:** rows whose `Win` isn't Aff/Neg (closeouts such as "EMORY GS ADVANCES", byes) are skipped. This replaced the same-school rule, which only ever matched labor closeouts.
- **Teams missing from entries:** both seasons rate them (`teams_from_rounds: True`). Labor has no entries files for `nu`, `ndt`, `kentuckyrr` or `dartmouthrr`. Turning this on for labor added 140 rounds and 4 ranked teams and republished 2025–26.
- **Team identity:** a team is a debater partnership, keyed by surnames (#10). If one debater changes partners, that's a new team.
- **Merges made so far:**
  - `Emory CrTa` → `Emory CT` (Cross & Taylor, labor)
  - `Southern California ZB` and `BR` stay separate: both debated at the same tournaments

## Evidence (2026-09-15, labor + Northwestern arms)

| Check | Result |
|---|---|
| Median σ, 5 passes vs 1 pass | labor 0.94 vs 1.90 · arms 1.51 vs 3.47 |
| Median σ, TTT prototype (γ = 25/300 per tournament) | labor 1.68 · arms 3.23; Spearman with 5-pass 0.998 / 0.997 |
| Winner-prediction accuracy of published "before" ratings | 80.7%, but these ratings have already seen the results |
| Same, from an honest single chronological pass | 72.8% overall · 74.1% after the first tournament · 79.1% in elims |
| Aff win rate | labor 47.7% · NU arms prelims 50.9% |

## Priority 1: what the site shows is overstated

### 1. Replace the 5-pass replay with TTT
- **Problem:** `run_pipeline` feeds every round through TrueSkill 5 times, so σ shrinks by about √5 with no new information.
  - Conservative scores are inflated: Emory GY is 39.0 under 5 passes vs 34.9 under one.
  - History deltas are computed from ratings that have already absorbed those same results.
- **Plan:** fit the leaderboard with `trueskillthroughtime`, one time step per tournament.
  - Scale to TrueSkill's defaults (μ 25, σ 25/3, β 25/6) so the site's numbers stay comparable.
  - Add a `requirements.txt`.
  - Run to convergence: labor still moved about 0.005 after 30 iterations at ε = 1e-3, but a fit only takes about 2 s.
- **Frontend:** leaderboard μ (smoothed) will no longer equal the last "After" value in history (forward pass). Label that on TeamPage.

### 2. Separate the ratings output from the history output
- **History:** `match_history_*.csv` comes from one forward chronological pass, so each "before" uses only earlier results.
- **Leaderboard:** `teams_*.csv` uses the TTT fit.

## Priority 2: model fit

### 4. Evaluation harness
- **Method:** for each tournament *k*, fit on tournaments before *k* and predict *k*.
- **Metrics:** log loss, Brier score, accuracy.
- **Baseline:** 72.8% accuracy.
- **Use it to:** tune β, γ/τ and priors, and to accept or reject #5–#9.

### 5. Model side advantage directly
- **Problem:** separate Aff and Neg ratings each see half the data and never appear on the site.
- **Proposal:** a global aff/neg offset, or one per tournament. Labor neg had a small edge (aff won 47.7%).

### 6. Use panel information in elims
- **Problem:** a 2–1 elim counts the same as a 3–0.
- **Options:** rate each ballot separately, or scale the update by ballot margin.
- **Data:** `Votes` exists in arms files and in newer-format labor elims. Older labor files have only `Aff, Neg, Win`.

### 7. Dynamics
- **Within a season:** tune γ to how fast teams actually improve.
- **Between seasons:** inflate σ explicitly.

### 8. Carry priors across seasons
- **Problem:** every arms team starts at μ = 25, σ = 8.33.
- **Proposal:** seed each partnership from its debaters' prior-season ratings, with σ inflated. Needs #10.

### 9. Speaker points (low priority)
- **Data:** arms prelim files have points per debater.
- **Proposal:** use them as a weak margin signal, only if the harness shows a gain.

## Priority 3: data hygiene and process

### 10. Identify teams by debater surnames, not code initials (in progress)
- **Why codes fail** (entries scan):
  - Labor has 10 codes that cover more than one pair. For example, `Dartmouth GH` is both Gonzalez Arce & Hant and Guo & Hatton, and both are exported as `GH` in the same Kentucky rounds. `Kansas BP` is Bauman & Persson at Texas and UK, and Blaser & Pace at Wake.
  - 4 pairs appear under several codes: `Kansas BP`/`PB`, `Dartmouth GH`/`GuHa`, `MInnesota HU` (typo), `MoState NS`/`Missouri State NS`.
  - Arms is clean (132 codes, 132 pairs).
- **Plan:**
  - Canonical key: sorted surnames from entries `Entry`.
  - For tournaments without entries, or for ambiguous codes, use the speaker names in the prelim points columns.
  - Drop the reversed-initials heuristic, `REVERSED_INITIALS_EXCEPTIONS`, and most `name_fixes`.
  - Keep a readable display name (school + code).

### 11. Validation script (`coding/validate.py`, in progress)
- **Checks:** config (unlisted prefixes, missing entries file, missing `TOURNAMENT_NAMES`); names missing from entries, with similar codes; byes and closeouts; duplicate teams in a round; missing prelim files; even-round side flips (≥90%) and record gaps (≤1.5 from R3), skipped for fields under 16; bracket advancement; ballot counts vs result.
- **Calibration:** clean on every labor and arms tournament, apart from the round robins (now skipped). It flags the duplicate `Dartmouth GH` in UK R1–6.

### 12. Remaining cleanups
- **Eligibility:** once σ is honest, consider ranking by conservative score or showing σ bands, rather than filtering by tournament count.
- **Storage:** keep data canonical in git. The Dropbox move left 0-byte placeholders and a broken `.git`.
