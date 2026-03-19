# Adding a New Tournament

## 1. Add an entries file

Create `coding/data_labor/{tournament}_entries.csv` with a `Code` column listing every team attending:

```
Institution,Location,Entry,Code,Record
Texas,TX/US,Alemu & Richardson,Texas AR,
Texas,TX/US,Bhatt & Nguyen,Texas BN,
...
```

The `Code` column is the canonical team name. Only `Code` is required — extra columns are ignored.

> Teams already in a previous entries file don't need to be re-listed. `init_teams` merges and deduplicates all `*_entries.csv` files automatically.

## 2. Add round files

Create one CSV per round in `coding/data_labor/`, named `{tournament}_{round}.csv`:

```
coding/data_labor/
  texas_1.csv
  texas_2.csv
  ...
  texas_dubs.csv
  texas_octas.csv
  texas_quarters.csv
  texas_semis.csv
  texas_finals.csv
```

Each file must have exactly these three columns:

```
Aff,Neg,Win
Texas AR,Kansas LS,Aff
Michigan BP,Emory GS,Neg
...
```

`Win` accepts `Aff`, `Neg`, `AFF`, or `NEG` (case insensitive).

## 3. Register the tournament in `pipeline.py`

Add the tournament code to `TOURNAMENT_ORDER` in the correct chronological position:

```python
TOURNAMENT_ORDER = ['nu', 'uk', 'gonzaga', 'wake', 'gt', 'texas']
```

This is the only line you need to edit in `pipeline.py`. All round files for the new tournament are discovered automatically — no need to list individual rounds.

## 4. Register the display name in `frontend/src/utils/data.js`

Add the tournament to `TOURNAMENT_NAMES` so the frontend shows the full name instead of the code:

```js
const TOURNAMENT_NAMES = {
  nu: 'Northwestern',
  uk: 'Kentucky',
  gonzaga: 'Gonzaga',
  wake: 'Wake Forest',
  gt: 'Georgetown',
  texas: 'Texas',       // ← add this
}
```

If you skip this step, the frontend will display `TEXAS` (the code uppercased) — so it's optional.

## 5. Fix any team name inconsistencies

If the tournament's data uses different spellings for existing teams (e.g. `"Kansas LS "` with a trailing space, or `"Baylor MP"` vs `"Baylor PM"`), add the fix to `TEAM_NAME_FIXES` in `pipeline.py`:

```python
TEAM_NAME_FIXES = {
    ...
    'Kansas LS ': 'Kansas LS',   # ← trailing space fix
}
```

## 6. Re-run the pipeline

```bash
cd coding
python run.py
```

This regenerates `teams_labor.csv` and `match_history.csv` from scratch with all tournaments included, then copies both files to `frontend/public/data/` automatically.

To preview the updated frontend:

```bash
cd frontend
npm run dev
```

---

## Round naming conventions

| Pattern | Example | Meaning |
|---|---|---|
| `{t}_{n}` | `texas_1` | Preliminary round N |
| `{t}_dubs` | `texas_dubs` | Double-octafinals |
| `{t}_octas` | `texas_octas` | Octafinals |
| `{t}_quarters` | `texas_quarters` | Quarterfinals |
| `{t}_semis` | `texas_semis` | Semifinals |
| `{t}_finals` | `texas_finals` | Finals |

Within a tournament, prelim rounds are sorted numerically and elims are sorted in the order above — this controls the chronological match history shown on team pages.
