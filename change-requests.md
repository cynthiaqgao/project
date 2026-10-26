# Change requests

## Claims

| Person | Feature | Number | Evidence contributed |
|---|---|---|---|
| Xinyun Gu | Map hover data (U3/U4), checked at the backend level because the team has no `app.py` yet | Within-budget listing share (U1) | Direct listing-level count and a hand-calculated two-listing case on the Phase 2 backend and cleaned CSV; shows the selected map table lacks the pre-budget budget fields. |

## CR-XG-01 — Include pre-budget affordability in selected map data

- **Status:** Open.
- **Finding:** With a $200 budget and two eligible listings at $100 and $300, `affordability_map` correctly reports 1/2 = 50%, but the selected `map` table reports null `within_budget_n` and `within_budget_share` and has no `pre_budget_price_n` column. On the supplied CSV with default room and stay filters and a $250 budget, overall affordability is 3,773 / 15,412 = 24.4809% (correct), but all 229 rows of the selected `map` table have a null budget share.
- **Requirement:** `BUILD_SPEC.md` §4 (Map hover/click): selected price and inventory, plus joined pre-budget numerator and share and an explicitly labeled pre-budget denominator; selected `price_n` must never be labeled as the budget denominator.
- **Requested change:** In `geographic_summary()` / `dashboard_data()`, join `within_budget_n`, `within_budget_share` and a new `pre_budget_price_n` from the pre-budget summary into `map`, one-to-one by `neighbourhood` and `room_type`, keeping the selected `price_n`. When the app is built, check hover labels with a budget on, and with no selected listings but a positive pre-budget count. `phase2/FRESH_AGENT_TEST.md` (Q7) says this join was already added; if it exists on the team's main branch, close this request with that commit and a hover check.
- **Evidence:** `my-audit.md` and `audit_check.py` (run from the project folder with Python 3.10+ and pandas).
- **Limit:** The supplied archive has no `app.py`, so no rendered hover was checked, and I did not check the team's main branch for a newer backend.
