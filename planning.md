# Planning

Open work on the rating pipeline (`coding/pipeline.py`) and the frontend (`frontend/src/`). CLAUDE.md covers how the pipeline works and README.md covers data entry. Settled questions get one line each.

## Benchmarks

To count as an improvement, a change has to beat these walk-forward scores:

| Run | Matches | Accuracy | Log loss |
|---|---|---|---|
| `evaluate.py labor --priors energy` | 3246 | **75.1%** | **0.5136** |
| `evaluate.py arms --priors labor` (nu, kentuckyrr, uk, minn, harvard, wake) | 2133 | 70.8% | 0.5491 |
| `evaluate.py energy --priors nukes` | 2835 | 72.7% | 0.5323 |
| `evaluate.py nukes --priors personhood` | 2833 | 73.3% | 0.5346 |
| `evaluate.py personhood --priors antitrust` | 2562 | 72.6% | 0.5269 |
| `evaluate.py antitrust --priors alliances` | 2259 | 72.2% | 0.5297 |
| `evaluate.py labor` (unseeded, opener not scored) | 2783 | 71.7% | 0.5451 |
| `evaluate.py energy` (unseeded, opener not scored) | 2396 | 71.3% | 0.5572 |
| `evaluate.py nukes` (unseeded, opener not scored) | 2436 | 70.9% | 0.5559 |
| `evaluate.py personhood` (unseeded, opener not scored) | 2212 | 70.3% | 0.5588 |
| `evaluate.py antitrust` (unseeded, opener not scored) | 1910 | 70.3% | 0.5540 |
| `evaluate.py alliances` (no prior season) | 2149 | 67.5% | 0.5929 |

Seeded and unseeded runs score different match sets, because seeding makes the opener scorable. Compare a change against a row of the same kind.

These are on the full re-export (2026-10-07): every prelim in all three seasons has judges and speaker points, every elim has its panel split, and energy runs through ADA and the NDT. Nukes (2023–24), personhood (2022–23), antitrust (2021–22) and alliances (2020–21) were added on 2026-11-08 with the same coverage. Personhood's NDT is missing the Emory GK vs Michigan PP semi. Alliances' Fullerton–Georgetown has a Southern California JH whose rows carry no speaker names, so it is rated by code. The only code not tied to debaters is one nukes Harvard round (R5) for Harvard LM, where Lupica switched partners from Wang to Mukherjee mid-tournament.

## Open

- **Possible transfers, unconfirmed.** Same initial and surname at a new school the next season, and gone from the old one. Add the real ones to `SEASONS[season]['transfers']` and delete the rest.
  - energy → labor: B. Lemaster (Oklahoma → Kansas), J. Parrish (Minnesota → Utah), V. Patel (Iowa → Wake Forest).
  - labor → arms: A. Hendrix (Houston → Western Kentucky), E. Garza (UT San Antonio → Texas), J. Raines (Kansas State → Washburn), N. Patel (Binghamton → Michigan State), J. Song (West Point → Dartmouth).
- **Older seasons are still slightly over-trusted.** With growth and `DEBATER_INFLATION` = 4, chaining nukes costs arms about 0.003 nats against an energy-rooted chain. Antitrust helped nukes (−0.0020) but cost energy (+0.0020) and arms (+0.0011); alliances then helped every season but arms (personhood −0.0058, labor −0.0010, arms +0.0001). `DEBATER_INFLATION` 5 and 6 are no better on the seven-season chain. Growth by experience is now in (see Settled). Still untried: a carry that widens with the seasons since a debater was last seen; today a debater who misses a season is dropped from the chain.
- **Possible transfers, unconfirmed (common surnames):**
  - personhood → nukes: B. Smith (Oklahoma → James Madison), J. Campbell (Wyoming → Missouri State), B. Hines (Kansas → Northwestern), M. Ramesh (Pennsylvania → Northwestern), K. Williams (Central Oklahoma → Southern Nazarene).
  - antitrust → personhood: J. Crowley (Wake Forest → Western Washington), L. Smith (Central Oklahoma → Wichita State).
  - alliances → antitrust: A. White (Wake Forest → Georgetown), E. Bennett (Iowa → Michigan State), C. Smith (Baylor or Missouri State → Wake Forest).
- **Eligibility.** σ is no longer shrunk by replays, so consider ranking by conservative score or showing σ bands, instead of the `MIN_TOURNAMENTS` filter.
- **Judges are unused.** Every prelim now names its judge. The only thing tried is a leniency adjustment to speaker points, which didn't help.

## Settled

- **Model:** TTT over the season, one step per tournament, for the leaderboard; each round's exact share of that fit for match history (`season_contributions`, Nov 2026), so the history adds up to the leaderboard μ and judges each round against the opponent's whole-season rating; it replaced the forward pass's "rating at the time" numbers. Superseded (Nov 2026): history now shows each round's leave-one-out impact w(m − μ)/(1 − w) as Δ, so losses are always negative (shares from the prior read "+" on ~1,600 losses); Before/After are the forward estimate per tournament. A "Played like" (message mean) column was tried and dropped as confusing; `*_Perf` is still exported. Δ is within ~5% of exact refits, which would cost ~1 s per round. TTT beats forward out of sample (labor seeded 73.4% / 0.5309 vs 73.1% / 0.5326; energy 71.2% / 0.5596 vs 70.1% / 0.5722). The old 5-pass replay was dropped because it shrank σ about √5 with no new information.
- **Scale:** μ 25, σ 25/3, β 5.0, γ 25/300 per tournament, ε 1e-4. γ is flat from 0 to 8× in every season, since one season is too short for drift.
- **β = 5.0 (Nov 2026), up from 25/6.** The model was overconfident (logit slope 0.83–0.86). On all six seeded seasons with the new growth, 5.0 lowers log loss in every one (−0.0019 to −0.0048) and Brier is equal or better; accuracy moves ±0.3 by season (arms −0.2). 6.25 is too far. The debater fit keeps (25/6)/√2, the value growth and inflation were tuned with.
- **Draws / non-decisive rows:** `draw_probability=0`. Closeouts and byes are skipped.
- **Side advantage (#5): none.** The best global offset (−0.5, towards the neg) is worth 0.0012 nats in labor and 0.0002 in energy. Aff/Neg side ratings were removed. Rechecked across all seven seasons (Nov 2026): the best offset is within ±0.25 of 0 in every one. Arms' elims run 56% aff (CME's rankings adjust for this), but every earlier season's elims run 44–50%, so an elim-only offset would be fitting noise.
- **Ballot margins (#6): off.** With every elim's split now in the data, one match per ballot gains 0.0028 nats in energy but loses 0.0011 in labor and 0.0033 in arms. Judges on one panel aren't independent. Revisit only as a weighted single match. Across all seven seasons (14,903 rounds): 70.24% / 0.5652 off vs 70.18% / 0.5641 on, a wash.
- **Cross-season priors (#8): shipped, and the largest gain so far.** Labor's opener goes from 50.0% to 71.5%; the rest of the season, on the same matches, goes from 71.8% to 74.1%. The gain fades by the NDT, as it should.
  - `PRIOR_INFLATION` is 2, down from 4: +0.4 points of accuracy in both labor and arms (0.5310 → 0.5286, 0.5777 → 0.5747). The seeds were too loose, not too tight: the opener's logit slope was 1.46 in labor and 1.05 in arms.
  - `DEBATER_INFLATION` (the per-season carry down the chain) is 4, up from 4/√2 once five seasons were chained: energy 0.5338 → 0.5333, labor 0.5201 → 0.5193, arms 0.5596 → 0.5589. 5 and 6 are no better. Halving it costs arms 0.006 nats.
  - `DEBATER_GROWTH` = 1.0 is added to each returning debater's carried mean, both down the chain and in the seed. Returning debaters rise +0.75 to +1.0 a year in every pair of seasons. Without growth, chaining nukes made labor (0.5286 → 0.5329) and arms (0.5650 → 0.5723) worse; with it, they reach 0.5179 and 0.5599. Published μ rises in later seasons as a result (+2 labor, +3 arms), but rankings barely move.
  - Growth now depends on experience (Nov 2026): `DEBATER_GROWTH` = (1.5, 1.0), +1.5 after a debater's first season in the data and +1.0 after later ones (`debater_experience` counts consecutive seasons rated). It beats flat +1 in all six seeded seasons (pooled log loss 0.5347 → 0.5329, accuracy 72.8% → 73.0%). (2.0, 1.0) is better pooled (0.5324) but worse for arms; less than +1.0 for later years is worse everywhere. The data starts in 2020–21, so "first season" means first seen, not first-year.
- **Speaker points (#9): redundant with the rating.** Now tested with full coverage: stack the model's logit with each team's past points margin, fit the weights on one season, score another. Five of six season pairs get worse (−0.0003 to −0.0077 nats); only labor → energy gains (+0.0013), and energy is the unseeded season. Adjusting for judge leniency doesn't change it.
- **Team identity:** a sorted-surname partnership, resolved from entries, then speaker names, then the nearest tournament's code, then initials, then the bare code.
- **Debater identity:** `School/initial.surname`, with the first initial read from the points column (100% coverage). `identify_debaters` turns that into an id that stays with a person across seasons, exported as `Debater_IDs` and used for both the priors and the team page's cross-season links.
  - Initials separated every same-surname pair that used to be dropped as ambiguous (Emory's C. and J. Yang, the Wangs, Kansas's Sulemans, Missouri State's Neals), and Western Kentucky's two Ingrams across seasons.
  - `transfers`: Christiansen (CSU Long Beach → Southern California), Pieropan (Iowa → Kansas) and Parrish (Missouri State → Minnesota) in antitrust; Babcock (Johnson County CC → Wichita State) and Stinson (Tufts → UMass Amherst) in personhood; Reed-Valizan (Emporia State → Wichita State), Penumetcha (Indiana → UTD), Dal Pra (Kentucky → West Georgia), Dover (Mary Washington → George Mason), Ippagunta (Michigan → Georgia), Anderson McElligott (Minnesota → Iowa) in nukes; J. Park (Kansas → Michigan), Yarborough (Oklahoma → Southern Nazarene), Rezahusain (Wayne State → Binghamton) and Lassen (Wyoming → Baylor) in energy; Tahirkheli (Emory → Northwestern), Kaidar-Heafetz (West Georgia → Georgia) and Pack (Samford → Georgia) in labor; I. Song (Emory → Michigan) in arms. Arms has a second A. Tahirkheli at Emory, who is kept separate.
  - `NAMESAKES`: Dartmouth had two N. Cais in energy. The one who debated with Bald continues with Goldberg; the other (Wallace, Guddati) is a separate person.
  - `INITIAL_ALIASES`: Wake Forest's E. and L. Leverett are one person.
  - `SCHOOL_ALIASES` now also covers `Massachusetts, Amherst` → `UMass Amherst` and `Fullerton` → `Cal State Fullerton`. A hybrid entry's debaters are placed at the school they debate for alone, this season or an earlier one.
  - Worth about 0.010 nats on arms, where a wrong seed costs most, and almost nothing on labor.
- **Seasons:** alliances → antitrust → personhood → nukes → energy → labor → arms, chained by `prior_season`. Personhood uses labor's order. Antitrust and alliances have `fullertown` (Fullerton–Georgetown); alliances was online, with Northwestern twice (`nu1`, `nu2`), a Harvard RR and no Texas (its full-name export is Wake). Two exports had prelims out of order (antitrust Wake's R2 and alliances NDT's R2–R3 were re-created later); their order was recovered from side flips and power matching. Energy's tournament order was confirmed by hand and by seriation; nukes uses energy's order, with Long Beach in Georgetown's slot. Nukes' person-named maverick codes (`Hina Shehzad`, `Austin Davis`, …) are mapped to the school each pair debates for elsewhere via `name_fixes`. Nukes' Texas and personhood's Wake had triples rounds, so `_ELIM_ORDER` has `triples`. Personhood's Texas exported entry names ('Emory Giampetruzzi & Kessler') instead of codes. `_abbreviate_entry_names` turns them into codes ('Emory GK'), using two letters per surname where two would clash. Rows with a missing team or a blank result (byes, deleted entries) are skipped. `GMU` is a school alias for George Mason, and ` - ONL` is a truncated ` - ONLINE`. Antitrust's Kentucky RR used bare school names ('Kansas'); a bare school code takes its speakers' initials row by row, and maverick `name_fixes` now map to a bare school the same way, so a code carries both partners' initials. Speakerless rows reuse the code their raw name had at that tournament. Older schools renamed: `UT Dallas` → `UTD`, `UPenn` → `Pennsylvania`, `United States Military` → `West Point`, `UMass Amherst Policy` → `UMass Amherst`. `SCHOOL_ALIASES` now also match the first half of a hybrid.
- **Validation** (`validate.py`): side flips ≥90%, record gap ≤1.5 from R3, round robins skipped, missing elims detected, `CONSOLATION_ROUNDS` checked. Every tournament in all seven seasons passes.
- **Storage:** data is canonical in git. The Dropbox damage (empty placeholder files, broken `.git`) is gone, and `git fsck` is clean.

## Frontend

- **Load errors: done.** `useSeasonData` shows an error with a Retry button, and `parseCsv` drops a failed fetch from its cache.
