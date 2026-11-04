# Phase 2: LA Airbnb traveler dashboard foundation

This is the **team project**, preparing Phase 3. It does not revise Phase 1 or
replace earlier individual submissions. Start with [`../BUILD_SPEC.md`](../BUILD_SPEC.md).

For the Jupyter version, open
[`phase2_traveler_clean_team_data.ipynb`](../phase2_traveler_clean_team_data.ipynb)
and **Restart Kernel → Run All**. It shows the raw-data inspection, canonical
cleaning, missingness, record checks, typed export, traveler scenarios and backend
validation with executed outputs. The full cleaned dataframe is `team_data`.
Notebook tooling is listed in `requirements-notebook.txt`. To execute in a fresh
kernel from the repository root: `python -m phase2.execute_notebook`.

From the project repository root, with Python 3.10+:

```bash
python -m pip install -r phase2/requirements.txt
python -m phase2.build
python -m phase2.test_backend
```

For the existing workspace environment, use `../.venv/bin/python` in place of
`python`. These commands need no data downloads. The source is `LA_listings.csv`;
the canonical Phase 2 dataset is **`phase2/outputs/listings.csv`**. Earlier
`outputs/cleaned_listings.csv` and its summaries are historical artifacts and are
not Phase 2 inputs. No dashboard interface is required for this phase.

```python
from phase2.clean_data import load_listings
from phase2.backend import Filters, dashboard_data, compare_neighbourhoods

listings = load_listings()
views = dashboard_data(listings, Filters(trip_nights=7, budget_usd=250))
cards = views['overview']                 # Selected population
affordability = views['affordability']    # Pre-budget denominator
bars = views['segments']                  # Selected neighborhood-room summaries
budget_bars = views['affordability_segments']
comparison = compare_neighbourhoods(
    listings, Filters(trip_nights=7, budget_usd=250), ('Hollywood', 'Venice'))
```

| File | Role |
|---|---|
| `clean_data.py` | Canonical cleaning, explicit typed loader, source integrity rules |
| `backend.py` | Pure reusable traveler filtering, metrics, tables, CDF, map and comparison |
| `build.py` | Offline regeneration of all canonical artifacts |
| `test_backend.py` | Full-source reconciliation, edge cases and byte-identical rerun |
| `DATA_CONTRACT.md` | Source/derived column definitions, type and null semantics |
| `RECONCILIATION.md` | Reviewed team branches, conflicting rules and proposed resolutions |
| `READINESS.md` | Nine rubric criteria, evidence, unresolved submission gates |
| `outputs/audit.json` | Actual profiling, missingness, types, flags and source fingerprint |
| `outputs/manifest.json` | SHA-256 of reproducible outputs |
| `outputs/verification.json` | Actual automated test results |
| `outputs/default_*.csv` | Starting view tables: 7 nights, entire home, no budget |
| `outputs/budget250_*.csv` | Example $250/night scenario, with separate pre-budget tables |
| `outputs/example_comparison.csv` | Same-room Hollywood/Venice comparison under 7-night controls |

Only pandas is needed for the Phase 2 data/backend. For Phase 3, install
`python -m pip install -r phase2/requirements-dashboard.txt`; its Streamlit and
Plotly versions were exercised in the independent fresh-agent build. Start the
future interface with `python -m streamlit run app.py`. The isolated fresh-agent
build is validation evidence, not a claim that the final Phase 3 interface has
been accepted. Findings and fixes are recorded in `FRESH_AGENT_TEST.md`.
