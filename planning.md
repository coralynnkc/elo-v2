# Planning: methodology improvements

Open work on the rating pipeline (`coding/pipeline.py`), in priority order. Data-entry steps are in README.md.

## Decisions so far
- **Rating model:** the leaderboard uses TrueSkill Through Time (`fit_through_time`), with one time step per tournament. Match history is a separate single forward TrueSkill pass, so each "before" rating uses only earlier results.
  - **Scale:** μ 25, σ 25/3, β 25/6, γ 25/300 per tournament, so numbers stay comparable with TrueSkill's.
  - **Convergence:** ε = 1e-4 with a cap of 100 iterations. Labor needs 58 (about 4 s) and arms 2.
  - **Why:** the old 5-pass replay shrank σ by about √5 with no new information, and its history deltas had already absorbed the same results.
  - **Site:** leaderboard μ is smoothed over the season, so it can differ from a team's last history "After". TeamPage says so.
- **Draws:** `draw_probability=0`. Debate rounds can't be drawn.
- **Non-decisive rows:** rows whose `Win` isn't Aff/Neg (closeouts such as "EMORY GS ADVANCES", byes) are skipped. This replaced the same-school rule, which only ever matched labor closeouts.
- **Teams missing from entries:** both seasons rate them. Labor has no entries files for `nu`, `ndt`, `kentuckyrr` or `dartmouthrr`. Turning this on for labor added 140 rounds and 4 ranked teams.
- **Team identity:** a team is a debater partnership, keyed by normalized sorted surnames (`load_season`). If one debater changes partners, that's a new team.
  - **Resolution order:** that tournament's entries → speaker names in the points column → the partnership seen under the same code at the nearest tournament → the same with initials in either order → the bare code.
  - **Entries beat speaker names** because Tabroom shortens speaker names ("JSay" for Sayoto).
  - **Display name:** the code group (initials in any order) used at the most tournaments, shown alphabetically first so URLs stay stable. When partnerships share a code, surnames are appended: `Kansas BP (Bauman/Persson)`.
  - **Labor limit:** NU (no entries, no speaker names) leaves 12 codes rated by code.
- **Kentucky (labor) re-export:** `uk_1`–`uk_6` were re-exported with speaker points, because the old files had merged Dartmouth GH and HG.
- **Manual fixes:** `Emory CrTa` → `Emory CT` (Cross & Taylor), plus the older labor `name_fixes`, for codes with no names attached.
- **Evaluation:** `coding/evaluate.py` scores the model walk-forward — for each tournament, fit on the ones before it and predict it. Reports accuracy, log loss and Brier, split by prelim/elim and by whether both teams were already rated, against coin-flip and aff-base-rate baselines. `--sweep beta,gamma,aff-offset` scans a parameter; `--model forward` scores the history pass instead.
  - **Why walk-forward:** the 80.7% from the old 5-pass replay was not a forecast — those ratings had already seen the results.
- **Validation:** `coding/validate.py` runs before rating a tournament.
  - **Thresholds:** even-round side flip ≥90%; mean record gap ≤1.5 from R3; fields under 16 are treated as round robins and skipped.
  - **Calibration:** every labor and arms tournament passes. It caught the merged Dartmouth GH in the old Kentucky files.

## Evidence (2026-09-15, labor + Northwestern arms)

| Check | Result |
|---|---|
| Median σ, old 5-pass vs TTT | labor 0.95 → 1.76 · arms 1.54 → 3.24 |
| Rank agreement (Spearman on μ), 5-pass vs TTT | labor 0.999 (same top 10) · arms 0.997 |
| Winner-prediction accuracy of the old 5-pass "before" ratings | 80.7%, but these ratings had already seen the results |
| Same, from the forward-pass history | labor 72.8% overall · 74.1% after the first tournament · 79.1% in elims · arms 66.6% |
| Aff win rate | labor 47.7% · NU arms prelims 50.9% |

## Evidence (2026-09-15, walk-forward on labor, 2783 matches)

Out-of-sample, so these are lower than the replay numbers above and directly comparable to each other.

| Setting | Accuracy | Log loss | Brier |
|---|---|---|---|
| TTT (current) | 71.6% | 0.5528 | 0.1856 |
| Forward pass (match history) | 71.3% | 0.5584 | 0.1875 |
| Coin flip | 50.0% | 0.6931 | 0.2500 |
| Always pick neg (aff won 48.2%) | 51.8% | 0.6925 | 0.2497 |

- **TTT beats the forward pass out-of-sample**, which is independent support for rating the leaderboard with it.
- **Where the skill is:** 76.8% when both teams are already rated, 60.3% when one isn't; 77.2% in elims, 71.2% in prelims. Accuracy climbs over the season (67.7% at Kentucky, the first tournament with anything to fit on, → 81.3% at the NDT).
- **β:** flat. 1.5× the default (6.25) is best by 0.005 nats of log loss, with no accuracy gain. Not worth changing.
- **γ:** completely flat from 0 to 8× the default — one season is too short for drift to show. The current 25/300 is as good as turning it off.
- **Global aff offset:** best at −0.25 to −0.5 skill points (a slight neg edge), worth 0.0008 nats. Noise.

## Priority 2: model fit

### 5. Model side advantage directly — **rejected as a global offset**
- **Result:** the sweep above found no useful global aff/neg offset. The side effect is real but far smaller than a rating point.
- **Still open, low priority:** a per-tournament offset, and dropping the unused Aff/Neg side ratings from the forward pass (they each see half the data and never reach the site).

### 6. Use panel information in elims
- **Problem:** a 2–1 elim counts the same as a 3–0.
- **Options:** rate each ballot separately, or scale the update by ballot margin.
- **Data:** `Votes` exists in arms files and in newer-format labor elims. Older labor files have only `Aff, Neg, Win`.

### 7. Dynamics
- **Within a season:** settled — γ makes no measurable difference over one season (see above). Keep 25/300.
- **Between seasons:** inflate σ explicitly. Untested until a second season can be chained; needs #8.

### 8. Carry priors across seasons
- **Problem:** every arms team starts at μ = 25, σ = 8.33.
- **Proposal:** seed each partnership from its debaters' prior-season ratings, with σ inflated. `Debaters` provides the surnames, but individuals are keyed by surname only, so shared surnames (Shah, Smith) need care.

### 9. Speaker points (low priority)
- **Data:** arms prelim files have points per debater.
- **Proposal:** use them as a weak margin signal, only if the harness shows a gain.

**Bar for #6, #8 and #9:** beat 0.5528 log loss on labor walk-forward. Given how flat β and γ turned out, only changes that add *information* (ballot margins, prior-season priors, speaker points) are likely to move it.

## Priority 3: data hygiene and process

### 12. Remaining cleanups
- **Eligibility:** σ is no longer shrunk by replays, so consider ranking by conservative score or showing σ bands, rather than filtering by tournament count.
- **Storage:** keep data canonical in git. The Dropbox move left 0-byte placeholders and a broken `.git`.
