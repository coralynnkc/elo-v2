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
- **Seasons:** energy (2024–25) → labor (2025–26) → arms (2026–27), chained by `prior_season`.
  - **Energy order:** `nu, kentuckyrr, uk, harvard, wake, georgetown, dartmouthrr, texas`, confirmed by Cora. Seriation on 137 team codes (each code should occupy a contiguous run of tournaments) independently pins `nu → uk → wake → texas`; it can't fix the direction or place Georgetown and Harvard.
  - **Energy quirks:** everything is old-format, so no ballot margins and no speaker names outside the two round robins, whose exports are school-only and were renamed from their Tabroom IDs. `texas` has no entries file. Harvard ran a third-place debate between its semis losers, kept as `semis_2`.
- **Cross-season priors:** a season with a `prior_season` in `SEASONS` seeds its teams from that season's debater ratings. `fit_debaters` runs the same TTT fit with each side as a two-player team, so partners split the credit; `seed_priors` adds a new partnership's two debaters (means add, variances add) plus `PRIOR_INFLATION` = 4 skill points. Arms is seeded from labor.
  - **Debater key:** school and normalized surname. Surname alone merges eight different Smiths; school and surname leave 4 clashes in labor and 3 in arms, which `_ambiguous_debaters` finds automatically (a key on two teams at one tournament must be two people) and drops.
  - **Coverage:** 107 of 135 arms teams. A team with one returning debater is seeded from that debater plus a default half-team prior, so it still starts above a wholly unknown team.
  - **Where it applies:** both the forward pass and the TTT fit, so a seeded team's first history `Before` is its seed rather than 25.
  - **Chaining:** `season_debaters` recurses through `prior_season`, so a debater's rating carries energy → labor → arms instead of restarting each year. `carry_debaters` widens it by `DEBATER_INFLATION` at each hop.
- **Ballot margins:** `load_season` parses the panel split from `Win` ("3-0 AFF") into `Ballots_Win`/`Ballots_Lose`. `round_matches(rd, split_ballots=True)` then rates a paneled round once per judge, so a 3-0 moves ratings further than a 2-1 with no tuned weighting. `SPLIT_BALLOTS` is **off, and settled** — labor's early elims were re-exported so margins now sit at the front of the season, and one ballot per judge still loses to one match per round (see below).
- **Validation:** `coding/validate.py` runs before rating a tournament.
  - **Thresholds:** even-round side flip ≥90%; mean record gap ≤1.5 from R3; fields under 16 are treated as round robins and skipped. A round is reported missing when more than a third of an elim round's winners never appear again — closeouts and byes drop one or two, not half the field.
  - **Consolation rounds:** `CONSOLATION_ROUNDS` (`semis_2`) sit outside the bracket chain; their field is checked to be exactly the previous round's losers.
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

### Cross-season priors, scored on the first arms tournament

Every team at a season's opener is a cold start, so without priors the model can only guess. `evaluate.py arms --priors labor` scores exactly that, on 556 matches:

| Setting | Accuracy | Log loss | Brier |
|---|---|---|---|
| Seeded from labor debaters | 66.6% | 0.6051 | 0.2079 |
| No priors (coin flip) | 50.0% | 0.6931 | 0.2500 |

- **The largest gain so far**, and the only change that has beaten flat priors by more than noise.
- **Inflation:** swept 1–12; 4 is the minimum, and the curve is shallow between 2 and 6.
- **Effect on the site:** arms median σ 3.24 → 2.97, Spearman 0.99 against the unseeded leaderboard, the top 6 unchanged. Labor is byte-identical, since it has no prior season.

## Priority 2: model fit

### Cross-season priors, second test: labor seeded from energy (2026-09-15)

Adding energy gives the priors idea a much bigger test than arms' 556 matches — and unlike arms, labor has nine further tournaments to show downstream effects.

**Labor's opener stops being a coin flip.** 463 matches at Northwestern, none of them previously scorable:

| | Accuracy | Log loss |
|---|---|---|
| Seeded from energy | 70.7% | 0.5706 |
| No priors | 50.0% | 0.6931 |

**And the whole season improves,** on the identical 2783 matches that were scorable either way:

| | Accuracy | Log loss |
|---|---|---|
| No priors | 71.6% | 0.5528 |
| Seeded from energy | **73.2%** | **0.5372** |

Every tournament improves except the 21-match Kentucky RR. The gains are largest where a team's own season record is still thin — `ada` −0.1055, `gt` −0.0306, `gonzaga` −0.0115 — and vanish by the NDT (−0.0003), where nine tournaments of current-season data have long since swamped the prior. That is exactly the shape a good prior should have.

Energy's own walk-forward, with no season before it, is 70.7% / 0.5688 on 1878 matches.

### Ballot margins (2026-09-15, re-tested 2026-09-16)

The margin is in the `Win` column, not just `Votes`: after re-exporting labor's early elims, 537 of labor's 3264 rows (16.5%) and 27 of arms' 559 read "3-0 AFF" or "2-1 NEG".

**The signal is real and large.** Split decisions happen when the round was close; unanimous ones when it wasn't:

| Panel result | n | Model P(winner wins), computed beforehand |
|---|---|---|
| Unanimous (3-0, 5-0) | 300 | 0.799 |
| Split (2-1, 3-2, 4-1) | 237 | 0.587 |

That gap is +0.212, se 0.019, z = +11.0.

**Rating on it still doesn't pay.** The 2026-09-15 test was starved of data — every margin sat at the end of the season. Re-exporting `nu`, `uk`, `gonzaga`, `wake` and `gt` elims (25 files, 140 rows) put margins at the front, where they can inform seven downstream tournaments. Walk-forward on labor, seeded from energy:

| | Accuracy | Log loss |
|---|---|---|
| Baseline | 72.9% | 0.5420 |
| `--ballots` | 72.6% | 0.5427 |

- **It is now slightly worse, not slightly better**, and worse at every β in the sweep (best with ballots 0.5393 at β = 6.25, against 0.5381 without). Per tournament the sign is mixed: `ada` and `gt` improve, `gonzaga`, `uk` and `dartmouthrr` get worse.
- **Cost:** labor median σ 1.76 → 1.54. Three judges watching one debate aren't three independent observations, and that overcounting is what the log loss is now picking up.
- **Verdict:** shipped but off, and the data excuse is gone. The signal belongs in a *weighting* of one match, not in three matches; that would need a tuned knob, so it is only worth building if something else runs out first.
- **Kept from the re-export:** the new files carry `Judges` and `Votes`, so the panel composition is available for any later judge-level work. Team identities, the 177-team leaderboard and the top 10 are unchanged (max |Δμ| 0.03).

### 5. Model side advantage directly — **rejected as a global offset**
- **Result:** the sweep above found no useful global aff/neg offset. The side effect is real but far smaller than a rating point.
- **Still open, low priority:** a per-tournament offset, and dropping the unused Aff/Neg side ratings from the forward pass (they each see half the data and never reach the site).

### 6. Use panel information — **built, off, closed**
- Implemented as one match per ballot (see above). The re-export it was waiting on is done, and it did not clear the bar; one ballot per judge overstates a panel's independence. Reopen only as a weighted single match.
- **Not just elims:** NDT prelims are paneled too, so this reaches ordinary rounds wherever the export records a split.

### 7. Dynamics
- **Within a season:** settled — γ makes no measurable difference over one season (see above). Keep 25/300.
- **Between seasons:** done as part of #8 — `PRIOR_INFLATION` = 4 skill points, tuned by sweep.

### 8. Carry priors across seasons — **done**
- Shipped; see the evidence above. Shared surnames are handled by keying on school as well, and dropping the handful of keys that turn up on two teams at one tournament.
- **Confirmed twice:** arms from labor (+16.6 points of accuracy on the opener) and labor from energy (+23.2 on the opener, +1.6 across the whole season). See the evidence above.
- **Still open:** labor's 12 code-only teams contribute no debater ratings, and a debater who transfers schools (`Emory/Columbia AH`) loses their history, since the key includes the school.

### 9. Speaker points (low priority)
- **Data:** arms prelim files have points per debater.
- **Proposal:** use them as a weak margin signal, only if the harness shows a gain.

**Bar for #9:** beat 0.5528 log loss on labor walk-forward. Given how flat β and γ turned out, only changes that add *information* (ballot margins, prior-season priors, speaker points) are likely to move it.

## Priority 3: data hygiene and process

### 12. Remaining cleanups
- **Eligibility:** σ is no longer shrunk by replays, so consider ranking by conservative score or showing σ bands, rather than filtering by tournament count.
- **Storage:** keep data canonical in git. The Dropbox move left 0-byte placeholders and a broken `.git`.
