# Planning

Open work on the rating pipeline (`coding/pipeline.py`) and the frontend (`frontend/src/`). CLAUDE.md covers how the pipeline works and README.md covers data entry. Settled questions get one line each.

## Benchmarks

To count as an improvement, a change has to beat these walk-forward scores:

| Run | Matches | Accuracy | Log loss |
|---|---|---|---|
| `evaluate.py labor --priors energy` | 3246 | **72.9%** | **0.5420** |
| `evaluate.py arms --priors labor` (nu, kentuckyrr, uk) | 982 | 67.9% | 0.5938 |
| `evaluate.py labor` (unseeded, opener not scored) | 2783 | 71.6% | 0.5529 |
| `evaluate.py energy` (no prior season) | 1878 | 70.7% | 0.5688 |

Seeded and unseeded runs score different match sets, because seeding makes the opener scorable. Compare a change against a row of the same kind.

## Open

- **Arms priors are overconfident.** At Kentucky the logit slope is 0.63 ± 0.10; labor's is 0.89. `PRIOR_INFLATION` was tuned on labor from energy only, so re-sweep it on arms (`--sweep inflation`) once there are 4–5 tournaments.
- **Speaker points: recheck at 4–5 arms tournaments**, when coverage passes about 50% (see Settled).
- **School transfers are lost.** Surname matching can't handle them: common surnames (`smith`, `lee`, `jones`, `patel`) and surname-only entries files. If this is worth fixing, add a hand-checked list of moves to `SEASONS`, the way `name_fixes` works.
- **Labor's 12 code-only teams** (mostly from NU) pass no debater ratings to arms.
- **Eligibility.** σ is no longer shrunk by replays, so consider ranking by conservative score or showing σ bands, instead of the `MIN_TOURNAMENTS` filter.

## Settled

- **Model:** TTT over the season, one step per tournament, for the leaderboard; one forward pass for match history. TTT beats forward out of sample (71.6% / 0.5529 vs 71.3% / 0.5584). The old 5-pass replay was dropped because it shrank σ about √5 with no new information.
- **Scale:** μ 25, σ 25/3, β 25/6, γ 25/300 per tournament, ε 1e-4. β and γ are flat in sweeps, since one season is too short for drift. Between seasons, drift is handled by `PRIOR_INFLATION`/`DEBATER_INFLATION`.
- **Draws / non-decisive rows:** `draw_probability=0`. Closeouts and byes are skipped.
- **Side advantage (#5): none.** A global offset is worth 0.0008 nats. Per-tournament aff rates vary *less* than binomial noise (χ² p = 0.97 energy, 0.94 labor). Aff/Neg side ratings were removed.
- **Ballot margins (#6): off.** The signal is real (P(winner) 0.80 unanimous vs 0.59 split), but one match per ballot costs 0.0007 nats at every β, because judges aren't independent. Revisit only as a weighted single match. `Judges`/`Votes` are kept in the files.
- **Cross-season priors (#8): shipped, and the largest gain so far.** Labor's opener goes from 50.0% to 70.7%; the full season, on the same matches, goes from 71.6% to 73.2%. `PRIOR_INFLATION` = 4 (swept 1–12, shallow from 2 to 6). The gain fades by the NDT, as it should.
- **Speaker points (#9): redundant with the rating.** Labor stack: +0.001 nats, z = 1.6 in sample. Arms out of sample: +0.0055 ± 0.0034 nats.
- **Team identity:** a sorted-surname partnership, resolved from entries, then speaker names, then the nearest tournament's code, then initials, then the bare code. Teams missing from entries are still rated.
- **Debater keys:** `School/surname`. `SCHOOL_ALIASES` merges one school's two Tabroom names (`MoState`). A hybrid entry's debaters are placed at their other-season school.
- **Seasons:** energy → labor → arms, chained by `prior_season`. Energy's tournament order was confirmed by hand and by seriation.
- **Validation** (`validate.py`): side flips ≥90%, record gap ≤1.5 from R3, round robins skipped, missing elims detected, `CONSOLATION_ROUNDS` checked. Every labor and arms tournament passes.
- **Storage:** data is canonical in git. The Dropbox damage (empty placeholder files, broken `.git`) is gone, and `git fsck` is clean.

## Frontend

- **Search the leaderboard.** A season has 170+ teams, and finding one means scrolling. Add a filter box that matches team names and debaters.
- **Explain the numbers.** Header tooltips cover μ, σ and Conservative. A short "How ratings work" note would still help readers from outside debate stats: TTT, why the leaderboard μ differs from the last After, and what σ means. This could go with the σ-bands idea under Eligibility above.
- **Fewer decimals in match history.** Before, After and Δ show 3 decimals, and 1–2 would be easier to read. The leaderboard keeps 3 so columns line up.
- **Team page context.**
  - Show the overall record next to the Aff/Neg split.
  - Group match history by tournament, with collapsible headers.
  - Link to the same partnership in other seasons, using the same debater keys as the cross-season priors.
- **Shorten the leaderboard subtitle.** It lists every tournament inline, which gets long by the NDT. Use chips, or "through NDT (11 tournaments)".
- **Handle load errors.** A failed CSV fetch leaves "Loading…" up forever. Show an error message and a retry.
- **Share the table CSS.** `leaderboard-table`, `match-table` and `mini-table` repeat the same header and cell rules.
- **Light mode.** Colors are all `:root` tokens, so a light theme is one `prefers-color-scheme` block. The chart would need its own check against the light surface.
