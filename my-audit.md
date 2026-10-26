# Module 9 individual audit — Xinyun Gu

## Scope and version

- **Project:** LA Airbnb Traveler Comparison Dashboard (team project).
- **Version checked:** `project-main.zip` downloaded October 25, 2026, archive comment `974233619d115337db6bc5bf599f354e66b1d224`. It contains `BUILD_SPEC.md`, `phase2/backend.py`, `phase2/outputs/listings.csv` (43,932 cleaned listings) and `phase2/FRESH_AGENT_TEST.md`. It has no `app.py`, so **our team has not built the Phase 3 app yet**. The archive comment identifies the zip but cannot prove which commit is on `main`.
- **Feature:** geographic overview's map hover (U3/U4), audited at the level of the data it receives from the backend (`dashboard_data()['map']`), because there is no rendered UI to hover over yet.
- **Number:** within-budget listing share for the Explore view (U1).

## User and requirement

A traveler planning a seven-night stay in an entire home/apt wants to know what share of priced listings fits a $250 nightly budget, and then to hover over a neighborhood on the map. `BUILD_SPEC.md` §3 defines the share as the number of listings priced at or below the budget divided by **all observed prices before the budget is applied**, under the other active filters. §4 says the map hover keeps its selected-population price statistics and also shows the pre-budget budget numerator, share, and a separately named `pre_budget_price_n` denominator; selected `price_n` must never be labeled as the budget denominator.

## Check 1 — the budget number

I called `dashboard_data(d, Filters(budget_usd=250))` on the cleaned CSV, with all other filters at their defaults (all neighborhoods, Entire home/apt, seven planned nights, minimum reviews 0, high-price exclusion off). Separately, I counted rows directly with `room_type == 'Entire home/apt'` and `minimum_nights <= 7`, then counted nonmissing prices and prices <= 250 in that group.

| Quantity | Direct count from listing rows | Backend result |
|---|---:|---:|
| Pre-budget listings | 16,633 | 16,633 |
| Pre-budget observed prices (denominator) | 15,412 | 15,412 |
| Within-budget prices (numerator) | 3,773 | 3,773 |
| Within-budget share | 3,773 / 15,412 = 24.4809% | 24.4809% |
| Budget-selected listings | 3,773 | 3,773 |

The share is between 0 and 100%, is unitless, and uses the pre-budget denominator, as specified. Dividing by the 3,773 budget-selected prices instead would always give 100%, which would be misleading.

**Small case I can calculate by hand:** two otherwise identical eligible listings at $100 and $300 with a $200 budget should give one within-budget listing, two pre-budget observed prices, and 50%. The backend's `affordability` returned `within_budget_n=1, price_n=2, within_budget_share=0.5`, which matches.

## Check 2 — map hover data as a traveler would receive it

For the same two-listing case, `dashboard_data()['map']` returned one selected listing with `price_n=1` (correct for the selected population), but `within_budget_n=None`, `within_budget_share=NaN`, and **no `pre_budget_price_n` column**. A hover built from this table could not show the required budget numerator and denominator. The separate `affordability_map` table does give 1/2 = 50%, but it describes the pre-budget population, not the selected map's inventory and price.

On the real data at the $250 default, all 229 rows of `map` had a null budget share, so every marker would show no budget information.

**Cause:** `dashboard_data()` calls `geographic_summary(selected)` for `map` without passing the budget. `geographic_summary()` then calls `market_summary(d, budget_usd)` with its default `None`, and nothing joins the pre-budget values back in (`phase2/backend.py`, `geographic_summary()` and the `'map'` entry of `dashboard_data()`).

`phase2/FRESH_AGENT_TEST.md` (Q7) says this was fixed by joining by neighborhood and room type, but the `backend.py` in this archive does not contain that fix. Either the fix was not committed to the archive I was given, or the document is ahead of the code.

## Reproduction

`audit_check.py` (committed alongside this file) runs everything above. From the extracted project folder, with Python 3.10 or newer (the backend uses `X | None` annotations and fails on 3.9) and pandas installed:

```bash
python audit_check.py
```

I ran it with Python 3.12 and pandas from the current release. Expected output includes `3773 15412 0.2448092395535946` for the direct count, the same three values from `affordability`, the small case giving `within_budget_n 1, price_n 2, share 0.5` for `affordability`, null budget fields for `map`, `0` of `229` map rows with a budget share, and `pre_budget_price_n in map columns: False`.

## What this establishes and what it does not

- Established: the overall budget share is computed correctly for the default-room, 7-night, $250 example and for the hand-calculated small case; the selected map table in this archive cannot supply the specified budget numerator and denominator.
- Not established: how a rendered map hover looks or behaves (there is no app yet), keyboard behavior, other neighborhoods, room types or filter settings, or whether a newer backend on the team's main branch already fixes this.

## Conclusion and change request

The headline number is right; the map's data contract is incomplete. I filed **CR-XG-01** in `change-requests.md`: join the pre-budget numerator and share by neighborhood and room type into the selected `map` table, keep the selected `price_n`, add an explicit `pre_budget_price_n`, and when the app is built, verify the hover labels show the two populations separately.

## Individual contribution and AI use

I chose this feature and number, and I am responsible for the conclusions. An AI assistant helped me read the specification, write and run the checks, and draft this report. The numbers above come from running `audit_check.py` against the supplied CSV and backend, and I independently re-ran that script to confirm the output. I did not inspect a live app because none exists, and I am not claiming a teammate's audit as my own.
