# Planning: methodology improvements

Suggestions for the TrueSkill pipeline (`coding/pipeline.py`), ordered by priority. Numbers come from experiments run on 2026-09-15 against the 2025–26 (labor) data and Northwestern 2026 (arms).

## Evidence

| Check | Result |
|---|---|
| Median σ, 5 passes vs 1 pass | labor 0.94 vs 1.90 · arms 1.51 vs 3.47 |
| Rank agreement, 5 passes vs 1 (labor) | Spearman 0.994, same top 5 |
| Winner-prediction accuracy of published "before" ratings | 80.7%, but they have already seen the results |
| Same, from an honest single chronological pass | 72.8% overall · 74.1% after the first tournament · 79.1% in elims |
| Labor rounds dropped because a team is missing from entries | 140 of 3,254 (4.3%), across 20 teams |
| `draw_probability` 0.1 (run.py) vs 0 (pipeline default) | no meaningful difference |
| Aff win rate | labor 47.7% (all rounds) · NU arms prelims 50.9% |

## Priority 1: what the site currently shows is overstated

### 1. Stop replaying the same results
`run_pipeline` feeds every round through TrueSkill 5 times. TrueSkill treats each replay as new evidence, so σ shrinks roughly by √5 without any new information. The rank order barely changes (0.994). What changes is confidence:

- **Conservative score:** μ − 3σ is inflated. Emory GY's is 39.0 under 5 passes but 34.9 under one.
- **Early season:** after one tournament, arms σ ≈ 1.5 claims near-certainty from 8–13 debates.
- **Match history:** the final pass's `Before`/`After`/`Δ` values were computed from ratings that had already absorbed those same results. So the "most consequential rounds" list is distorted, and before-ratings look more predictive than they are (80.7% vs an honest 72.8%).

**Recommendation:** use TrueSkill Through Time (`trueskillthroughtime` on PyPI). It smooths ratings across the whole season in both directions, so ratings don't depend on round order and don't need replays. Its uncertainty estimates are also honest.

A lighter alternative:
- fit final ratings with a regularized Bradley–Terry / Thurstone model
- compute history deltas separately (see 2)

### 2. Separate the ratings output from the history output
- **History:** `match_history_*.csv` should come from a single forward chronological pass, so each row's "before" rating uses only earlier results.
- **Leaderboard:** `teams_*.csv` can use the smoothed or batch fit.

These are two different questions ("what did this round do at the time?" and "how good is this team?"), and one set of numbers can't answer both.

### 3. Don't drop rounds for teams missing from entries
When a team isn't on the entries list, all of its rounds are skipped, which also removes that evidence from its opponents' ratings.
- **Arms:** now rates these teams (`teams_from_rounds: True`). Texas AL, Wichita State MG and Wyoming LW were affected.
- **Labor:** still drops them (140 rounds) so the published rankings don't change. Flip it when you're willing to republish.

## Priority 2: model fit

### 4. Build an evaluation harness first
Everything below is a judgment call until it can be scored. Suggested setup:
- **Method:** for each tournament *k*, fit on tournaments before *k* and predict *k*.
- **Metrics:** log loss and Brier score, plus accuracy.
- **Baseline:** 72.8% honest accuracy.

Use the harness to tune β, τ and priors, and to accept or reject each change below.

### 5. Model side advantage directly
The pipeline keeps separate Aff and Neg ratings that each see half the data and never appear on the site. A single global aff/neg offset (or one per tournament) is cheaper and uses all the data. Labor aff won 47.7%, a small but real neg edge.

### 6. Use panel information in elims
- **Current behavior:** a 2–1 elim updates ratings exactly like a 3–0 or a one-judge prelim.
- **Options:** treat each ballot as a separate result against the same ratings, or scale the update by ballot margin.
- **Decide with:** the harness.

### 7. Tune dynamics (τ)
The default τ = 25/300 was designed for online games. Within a season, τ controls how fast ratings can move as teams improve.
- **Within seasons:** tune τ for the pace at which teams actually improve.
- **Between seasons:** inflate σ explicitly instead of relying on τ.
- **Replays:** currently apply τ 5 times per round. This goes away with 1.

### 8. Carry priors across seasons
Every arms team starts at μ = 25, σ = 8.33, even though most debaters competed last season. The entries files include debater names (`Entry`: "Gallagher & Young"). Seed each new team from its debaters' prior-season ratings, with σ inflated. This matters most right now, with only one tournament in.

### 9. Speaker points (lower priority)
Arms prelim files include speaker points per debater. They could serve as a weak margin signal, but points vary a lot by judge. Only worth adding if the harness shows a gain.

## Priority 3: data hygiene and process

### 10. Identify teams by debater surnames, not code initials
Codes are unstable: reversed initials, the `Kansas BP`/`Kansas PB` exception, `Emory ChSt`/`CrSm`, and one-off fixes such as `Wichita State MG`→`GM` (which was global until today). A canonical key of sorted surnames from the entries `Entry` column would:
- remove the reversed-initials heuristic and the exception list
- track partnerships reliably
- make 8 possible

### 11. Add a validation script for new tournaments (`coding/validate.py`)
Automate the checks run by hand for Northwestern:
- **File order:** sides flip between consecutive rounds (99% for NU R1→R2), and record gaps between opponents match power matching.
- **Byes:** rows with a blank team (3 at NU).
- **Names:** names in rounds but not in entries; reversed-initial pairs.
- **Bracket:** elim winners advance; closeouts show up as missing rows (2 at NU, both Michigan BS).

### 12. Smaller cleanups
- **Draw probability:** set `draw_probability=0` explicitly in `run.py`; debate has no draws. No ranking impact, but the two defaults currently disagree.
- **Same-school skip:** the rule treats a team code minus its last word as the school name. Tabroom exports already omit closeouts, so it now mostly guards against nothing. Check that it never fires on real prelim rounds, then drop it or log when it does.
- **Eligibility:** once σ is honest, consider ranking by conservative score or showing σ bands rather than filtering by tournament count.
- **Storage:** keep data canonical in git. The Dropbox move left 0-byte placeholders and a broken `.git`.

## Adding a tournament (current process)
1. Export rounds from Tabroom into `coding/data_arms/` as `<code>_<round>.csv` (`1`–`8`, `dubs`, `octas`, `quarters`, `semis`, `finals`), plus `<code>_entries.csv`.
2. Append `<code>` to `SEASONS['arms']['tournaments']` in `coding/pipeline.py`, in chronological order. If it's a new code, add a display name to `TOURNAMENT_NAMES` in `frontend/src/utils/data.js`.
3. `python coding/run.py` (current season; `all` reruns every season).
4. Once a second tournament is in, the two-tournament eligibility rule switches on and the "provisional" banner disappears automatically.
