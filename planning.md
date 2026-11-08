# Planning

Open work on the rating pipeline (`coding/pipeline.py`) and the frontend (`frontend/src/`). CLAUDE.md covers how the pipeline works and README.md covers data entry. Settled questions get one line each.

## Benchmarks

To count as an improvement, a change has to beat these walk-forward scores:

| Run | Matches | Accuracy | Log loss |
|---|---|---|---|
| `evaluate.py labor --priors energy` | 3246 | **74.8%** | **0.5181** |
| `evaluate.py arms --priors labor` (nu, kentuckyrr, uk, minn, harvard) | 1573 | 70.6% | 0.5601 |
| `evaluate.py energy --priors nukes` | 2835 | 72.4% | 0.5350 |
| `evaluate.py nukes --priors personhood` | 2833 | 72.9% | 0.5399 |
| `evaluate.py personhood --priors antitrust` | 2562 | 73.0% | 0.5341 |
| `evaluate.py antitrust --priors alliances` | 2259 | 71.6% | 0.5361 |
| `evaluate.py labor` (unseeded, opener not scored) | 2783 | 71.8% | 0.5472 |
| `evaluate.py energy` (unseeded, opener not scored) | 2396 | 71.2% | 0.5596 |
| `evaluate.py nukes` (unseeded, opener not scored) | 2436 | 71.0% | 0.5598 |
| `evaluate.py personhood` (unseeded, opener not scored) | 2212 | 70.3% | 0.5627 |
| `evaluate.py antitrust` (unseeded, opener not scored) | 1910 | 70.2% | 0.5584 |
| `evaluate.py alliances` (no prior season) | 2149 | 67.2% | 0.5979 |

Seeded and unseeded runs score different match sets, because seeding makes the opener scorable. Compare a change against a row of the same kind.

These are on the full re-export (2026-10-07): every prelim in all three seasons has judges and speaker points, every elim has its panel split, and energy runs through ADA and the NDT. Nukes (2023–24), personhood (2022–23), antitrust (2021–22) and alliances (2020–21) were added on 2026-11-08 with the same coverage. Personhood's NDT is missing the Emory GK vs Michigan PP semi. Alliances' Fullerton–Georgetown has a Southern California JH whose rows carry no speaker names, so it is rated by code. The only code not tied to debaters is one nukes Harvard round (R5) for Harvard LM, where Lupica switched partners from Wang to Mukherjee mid-tournament.

## Open

- **β is too small for log loss, but not for accuracy.** The model is overconfident within a season: the logit slope is 0.83–0.86 in all three seasons, and about 0.73 at each season's Kentucky. β = 5.2 fixes some of that (labor 0.5286 → 0.5276, arms 0.5747 → 0.5715, energy 0.5596 → 0.5569) but costs accuracy in labor (73.7% → 73.6%) and arms (69.3% → 69.1%), so it wasn't applied. Re-check with `--sweep beta` when arms has 4–5 tournaments.
- **Possible transfers, unconfirmed.** Same initial and surname at a new school the next season, and gone from the old one. Add the real ones to `SEASONS[season]['transfers']` and delete the rest.
  - energy → labor: B. Lemaster (Oklahoma → Kansas), J. Parrish (Minnesota → Utah), V. Patel (Iowa → Wake Forest).
  - labor → arms: A. Hendrix (Houston → Western Kentucky), E. Garza (UT San Antonio → Texas), J. Raines (Kansas State → Washburn), N. Patel (Binghamton → Michigan State), J. Song (West Point → Dartmouth).
- **Older seasons are still slightly over-trusted.** With growth and `DEBATER_INFLATION` = 4, chaining nukes costs arms about 0.003 nats against an energy-rooted chain. Antitrust helped nukes (−0.0020) but cost energy (+0.0020) and arms (+0.0011); alliances then helped every season but arms (personhood −0.0058, labor −0.0010, arms +0.0001). `DEBATER_INFLATION` 5 and 6 are no better on the seven-season chain. A carry that widens with the number of seasons since a debater was last seen, or growth that depends on experience (first-years improve most), might fix both. Labor and energy prefer more growth (1.5–2), but arms gets worse past 1.0.
- **Possible transfers, unconfirmed (common surnames):**
  - personhood → nukes: B. Smith (Oklahoma → James Madison), J. Campbell (Wyoming → Missouri State), B. Hines (Kansas → Northwestern), M. Ramesh (Pennsylvania → Northwestern), K. Williams (Central Oklahoma → Southern Nazarene).
  - antitrust → personhood: J. Crowley (Wake Forest → Western Washington), L. Smith (Central Oklahoma → Wichita State).
  - alliances → antitrust: A. White (Wake Forest → Georgetown), E. Bennett (Iowa → Michigan State), C. Smith (Baylor or Missouri State → Wake Forest).
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
  - `DEBATER_INFLATION` (the per-season carry down the chain) is 4, up from 4/√2 once five seasons were chained: energy 0.5338 → 0.5333, labor 0.5201 → 0.5193, arms 0.5596 → 0.5589. 5 and 6 are no better. Halving it costs arms 0.006 nats.
  - `DEBATER_GROWTH` = 1.0 is added to each returning debater's carried mean, both down the chain and in the seed. Returning debaters rise +0.75 to +1.0 a year in every pair of seasons. Without growth, chaining nukes made labor (0.5286 → 0.5329) and arms (0.5650 → 0.5723) worse; with it, they reach 0.5179 and 0.5599. Published μ rises in later seasons as a result (+2 labor, +3 arms), but rankings barely move.
- **Speaker points (#9): redundant with the rating.** Now tested with full coverage: stack the model's logit with each team's past points margin, fit the weights on one season, score another. Five of six season pairs get worse (−0.0003 to −0.0077 nats); only labor → energy gains (+0.0013), and energy is the unseeded season. Adjusting for judge leniency doesn't change it.
- **Team identity:** a sorted-surname partnership, resolved from entries, then speaker names, then the nearest tournament's code, then initials, then the bare code.
- **Debater identity:** `School/initial.surname`, with the first initial read from the points column (100% coverage). `identify_debaters` turns that into an id that stays with a person across seasons, exported as `Debater_IDs` and used for both the priors and the team page's cross-season links.
  - Initials separated every same-surname pair that used to be dropped as ambiguous (Emory's C. and J. Yang, the Wangs, Kansas's Sulemans, Missouri State's Neals), and Western Kentucky's two Ingrams across seasons.
  - `transfers`: Christiansen (CSU Long Beach → Southern California), Pieropan (Iowa → Kansas) and Parrish (Missouri State → Minnesota) in antitrust; Babcock (Johnson County CC → Wichita State) and Stinson (Tufts → UMass Amherst) in personhood; Reed-Valizan (Emporia State → Wichita State), Penumetcha (Indiana → UTD), Dal Pra (Kentucky → West Georgia), Dover (Mary Washington → George Mason), Ippagunta (Michigan → Georgia), Anderson McElligott (Minnesota → Iowa) in nukes; J. Park (Kansas → Michigan), Yarborough (Oklahoma → Southern Nazarene), Rezahusain (Wayne State → Binghamton) and Lassen (Wyoming → Baylor) in energy; Tahirkheli (Emory → Northwestern), Kaidar-Heafetz (West Georgia → Georgia) and Pack (Samford → Georgia) in labor; I. Song (Emory → Michigan) in arms. Arms has a second A. Tahirkheli at Emory, who is kept separate.
  - `NAMESAKES`: Dartmouth had two N. Cais in energy. The one who debated with Bald continues with Goldberg; the other (Wallace, Guddati) is a separate person.
  - `INITIAL_ALIASES`: Wake Forest's E. and L. Leverett are one person.
  - `SCHOOL_ALIASES` now also covers `Massachusetts, Amherst` → `UMass Amherst` and `Fullerton` → `Cal State Fullerton`. A hybrid entry's debaters are placed at the school they debate for alone, this season or an earlier one.
  - Worth about 0.010 nats on arms, where a wrong seed costs most, and almost nothing on labor.
- **Seasons:** alliances → antitrust → personhood → nukes → energy → labor → arms, chained by `prior_season`. Personhood uses labor's order. Antitrust and alliances have `fullertown` (Fullerton–Georgetown); alliances was online, with Northwestern twice (`nu1`, `nu2`) and a Harvard RR. Two exports had prelims out of order (antitrust Wake's R2 and alliances NDT's R2–R3 were re-created later); their order was recovered from side flips and power matching. Energy's tournament order was confirmed by hand and by seriation; nukes uses energy's order, with Long Beach in Georgetown's slot. Nukes' person-named maverick codes (`Hina Shehzad`, `Austin Davis`, …) are mapped to the school each pair debates for elsewhere via `name_fixes`. Nukes' Texas and personhood's Wake had triples rounds, so `_ELIM_ORDER` has `triples`. Personhood's Texas exported entry names ('Emory Giampetruzzi & Kessler') instead of codes. `_abbreviate_entry_names` turns them into codes ('Emory GK'), using two letters per surname where two would clash. Rows with a missing team or a blank result (byes, deleted entries) are skipped. `GMU` is a school alias for George Mason, and ` - ONL` is a truncated ` - ONLINE`. Antitrust's Kentucky RR used bare school names ('Kansas'); a bare school code takes its speakers' initials row by row, and maverick `name_fixes` now map to a bare school the same way, so a code carries both partners' initials. Speakerless rows reuse the code their raw name had at that tournament. Older schools renamed: `UT Dallas` → `UTD`, `UPenn` → `Pennsylvania`, `United States Military` → `West Point`, `UMass Amherst Policy` → `UMass Amherst`. `SCHOOL_ALIASES` now also match the first half of a hybrid.
- **Validation** (`validate.py`): side flips ≥90%, record gap ≤1.5 from R3, round robins skipped, missing elims detected, `CONSOLATION_ROUNDS` checked. Every tournament in all seven seasons passes.
- **Storage:** data is canonical in git. The Dropbox damage (empty placeholder files, broken `.git`) is gone, and `git fsck` is clean.

## Frontend

- **Handle load errors.** A failed CSV fetch leaves "Loading…" up forever. Show an error message and a retry. Not urgent. Note that `parseCsv` now caches the fetch promise, so a failed fetch stays cached until reload.
