# Test fixtures

## `monthly_fact.csv`

Snapshot of the production `monthly_fact` table that lets the validation
gate (`backend/tests/test_validation_gate.py`) run in CI without a DB.

The gate is the "non-negotiable" calibration check declared in the root
`CLAUDE.md`; if no fixture exists and `DATABASE_URL` isn't set,
`conftest.py` silently *skips* it. Checking the fixture in is what makes
the gate actually gate.

### When to regenerate

Only when an intentional calibration change shifts the regime numbers
(edits to `DEFAULT_PCT_PER_SIGMA`, the lens formulas, or the baseline
window). Day-to-day FRED revisions are well inside the ±2pp tolerances
and shouldn't require a refresh — if they do, that's a signal the
tolerances are too tight, not that the fixture is wrong.

### Regenerate

From a shell with the production `DATABASE_URL` available (e.g.,
sourced from the project `.env`):

```sh
python -c "
import os, pandas as pd
from sqlalchemy import create_engine
from backend.db_url import normalize_db_url

eng = create_engine(normalize_db_url(os.environ['DATABASE_URL']))
df = pd.read_sql(
    'SELECT obs_date, median_price, median_income, mortgage_rate_30y, '
    'oer_index, cs_hpi, zhvi, treasury_10y, cpi, real_dpi_per_capita '
    'FROM monthly_fact ORDER BY obs_date',
    eng,
    parse_dates=['obs_date'],
)
df.to_csv('backend/fixtures/monthly_fact.csv', index=False)
print(f'wrote {len(df)} rows')
"
```

Then run the gate locally before committing:

```sh
pytest backend/tests/test_validation_gate.py -v
```

All four regime tests must pass. If they don't, the gate is telling you
the calibration drifted — fix that *before* updating the fixture.
