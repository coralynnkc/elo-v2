# Planning

Open work on the rating pipeline (`coding/pipeline.py`) and the frontend (`frontend/src/`). CLAUDE.md covers how the pipeline works and README.md covers data entry. Settled questions get one line each.

## Benchmarks

To count as an improvement, a change has to beat these walk-forward scores:

| Run | Matches | Accuracy | Log loss |
|---|---|---|---|
| `evaluate.py labor --priors energy` | 3246 | **73.7%** | **0.5286** |
| `evaluate.py arms --priors labor` (nu, kentuckyrr, uk) | 982 | 69.3% | 0.5747 |
| `evaluate.py labor` (unseeded, opener not scored) | 2783 | 71.8% | 0.5472 |
| `evaluate.py energy` (no prior season) | 2396 | 71.2% | 0.5596 |

Seeded and unseeded runs score different match sets, because seeding makes the opener scorable. Compare a change against a row of the same kind.

These are on the full re-export (2026-10-07): every prelim in all three seasons has judges and speaker points, every elim has its panel split, and energy runs through ADA and the NDT. No code is left unresolved in any season.

## Open

- **β is too small for log loss, but not for accuracy.** The model is overconfident within a season: the logit slope is 0.83–0.86 in all three seasons, and about 0.73 at each season's Kentucky. β = 5.2 fixes some of that (labor 0.5286 → 0.5276, arms 0.5747 → 0.5715, energy 0.5596 → 0.5569) but costs accuracy in labor (73.7% → 73.6%) and arms (69.3% → 69.1%), so it wasn't applied. Re-check with `--sweep beta` when arms has 4–5 tournaments.
- **Possible transfers, unconfirmed.** Same initial and surname at a new school the next season, and gone from the old one. Add the real ones to `SEASONS[season]['transfers']` and delete the rest.
  - energy → labor: B. Lemaster (Oklahoma → Kansas), J. Parrish (Minnesota → Utah), V. Patel (Iowa → Wake Forest).
  - labor → arms: A. Hendrix (Houston → Western Kentucky), E. Garza (UT San Antonio → Texas), J. Raines (Kansas State → Washburn), N. Patel (Binghamton → Michigan State), J. Song (West Point → Dartmouth).
- **Eligibility.** σ is no longer shrunk by replays, so consider ranking by conservative score or showing σ bands, instead of the `MIN_TOURNAMENTS` filter.
- **Judges are unused.** Every prelim now names its judge. The only thing tried is a leniency adjustment to speaker points, which didn't help.

## Settled

- **Model:** TTT over the season, one step per tournament, for the leaderboard; one forward pass for match history. TTT beats forward out of sample (labor seeded 73.4% / 0.5309 vs 73.1% / 0.5326; energy 71.2% / 0.5596 vs 70.1% / 0.5722). The old 5-pass replay was dropped because it shrank σ about √5 with no new information.
- **Scale:** μ 25, σ 25/3, β 25/6, γ 25/300 per tournament, ε 1e-4. γ is flat from 0 to 8× in every season, since one season is too short for drift. β is under review (see Open).
- **Draws / non-decisive rows:** `draw_probability=0`. Closeouts and byes are skipped.
- **Side advantage (#5): none.** The best global offset (−0.5, towards the neg) is worth 0.0012 nats in labor and 0.0002 in energy. Aff/Neg side ratings were removed.
- **Ballot margins (#6): off.** With every elim's split now in the data, one match per ballot gains 0.0028 nats in energy but loses 0.0011 in labor and 0.0033 in arms. Judges on one panel aren't independent. Revisit only as a weighted single match.
- **Cross-season priors (#8): shipped, and the largest gain so far.** Labor's opener goes from 50.0% to 71.5%; the rest of the season, on the same matches, goes from 71.8% to 74.1%. The gain fades by the NDT, as it should.
  - `PRIOR_INFLATION` is 2, down from 4: +0.4 points of accuracy in both labor and arms (0.5310 → 0.5286, 0.5777 → 0.5747). The seeds were too loose, not too tight: the opener's logit slope was 1.46 in labor and 1.05 in arms.
  - `DEBATER_INFLATION` (the per-season carry down the chain) stays at 4/√2. Halving it with the seed costs arms 0.006 nats.
- **Speaker points (#9): redundant with the rating.** Now tested with full coverage: stack the model's logit with each team's past points margin, fit the weights on one season, score another. Five of six season pairs get worse (−0.0003 to −0.0077 nats); only labor → energy gains (+0.0013), and energy is the unseeded season. Adjusting for judge leniency doesn't change it.
- **Team identity:** a sorted-surname partnership, resolved from entries, then speaker names, then the nearest tournament's code, then initials, then the bare code.
- **Debater identity:** `School/initial.surname`, with the first initial read from the points column (100% coverage). `identify_debaters` turns that into an id that stays with a person across seasons, exported as `Debater_IDs` and used for both the priors and the team page's cross-season links.
  - Initials separated every same-surname pair that used to be dropped as ambiguous (Emory's C. and J. Yang, the Wangs, Kansas's Sulemans, Missouri State's Neals), and Western Kentucky's two Ingrams across seasons.
  - `transfers`: Tahirkheli (Emory → Northwestern), Kaidar-Heafetz (West Georgia → Georgia) and Pack (Samford → Georgia) in labor; I. Song (Emory → Michigan) in arms. Arms has a second A. Tahirkheli at Emory, who is kept separate.
  - `NAMESAKES`: Dartmouth had two N. Cais in energy. The one who debated with Bald continues with Goldberg; the other (Wallace, Guddati) is a separate person.
  - `INITIAL_ALIASES`: Wake Forest's E. and L. Leverett are one person.
  - `SCHOOL_ALIASES` now also covers `Massachusetts, Amherst` → `UMass Amherst` and `Fullerton` → `Cal State Fullerton`. A hybrid entry's debaters are placed at the school they debate for alone, this season or an earlier one.
  - Worth about 0.010 nats on arms, where a wrong seed costs most, and almost nothing on labor.
- **Seasons:** energy → labor → arms, chained by `prior_season`. Energy's tournament order was confirmed by hand and by seriation.
- **Validation** (`validate.py`): side flips ≥90%, record gap ≤1.5 from R3, round robins skipped, missing elims detected, `CONSOLATION_ROUNDS` checked. Every tournament in all three seasons passes.
- **Storage:** data is canonical in git. The Dropbox damage (empty placeholder files, broken `.git`) is gone, and `git fsck` is clean.

## Frontend

- **Handle load errors.** A failed CSV fetch leaves "Loading…" up forever. Show an error message and a retry. Not urgent. Note that `parseCsv` now caches the fetch promise, so a failed fetch stays cached until reload.
