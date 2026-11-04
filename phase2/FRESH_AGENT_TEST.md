# Fresh-agent build test: questions, guesses and changes

Date: October 16, 2026. Project: Los Angeles Airbnb traveler dashboard.

## Method and outcome

A separate Codex coding agent (`fresh_agent_test`) started without this chat's
history. It received the project repository and `BUILD_SPEC.md`, attempted the
Phase 3 build in an isolated copy, and reported questions/assumptions to the
coordinator. A different model/vendor is not necessary for this context-isolated
test. The agent actually created `app.py` and separate Explore, Compare and
Details views; this was not just a prose review or a backend subprocess run.

The complete independent record contains **27 questions/assumptions**, including
routine implementation choices and unresolved Phase 3 visual checks:
[independent agent findings](fresh_agent_evidence/INDEPENDENT_AGENT_FINDINGS.md).
The table below summarizes the material contract/implementation gaps; it does
not replace that complete record.

The isolated build is at `../../tmp/fresh_agent_phase3/` relative to the project
root. It is a test artifact, not the accepted Phase 3 dashboard. The input was a
copy of the current working repository, including uncommitted Phase 2 files,
not a clean checkout of a published main revision. Original input hashes and the
original spec are preserved in `fresh_agent_evidence/`.

**Result:** independent implementation and automated UI tests completed. Gaps
below were resolved in the original spec/backend. Original-repository backend
verification passes **13 tests**, including fresh-process regeneration. The
agent's initial backend run passed 10; its follow-up passed 12 before the final
vectorized-aggregation regression test was added. Its isolated UI report records
11 successful scenarios. This does not establish every Phase 3 visual acceptance
criterion or team approval/merge to main.

## Questions and material guesses

The agent raised these issues to the coordinator or explicitly identified them
as choices needed to proceed. They were not questions submitted to the user.

| ID | Question / guess encountered | Decision and change |
|---|---|---|
| Q1 | Which Streamlit/Plotly versions should be installed? The spec names them, but Phase 2 requirements only include pandas. | Added `requirements-dashboard.txt`: pandas 2.3.3 through Phase 2 requirements, Streamlit 1.65.0, Plotly 7.1.0; versions actually installed in the fresh build. BUILD_SPEC §6 now specifies installation and startup commands. |
| Q2 | With multiple room types selected, may KPI prices/reviews be pooled? The initial spec only explicitly allowed a mixed global count. | Separate four-card KPI rows by room type. Only an optional combined listing count may carry a Mixed room types label. BUILD_SPEC §2 clarified. |
| Q3 | Does clicking a room-specific map marker or segment row select neighborhood only, or neighborhood plus room type? | Neighborhood-only detail scope; retain global room selections; highlight all rows for that neighborhood. BUILD_SPEC §4 clarified. |
| Q4 | When the budget leaves zero selected listings but pre-budget listings exist, should every chart disappear? | Selected metrics show zero/N/A; retain explicitly labeled pre-budget CDF, affordability and comparison evidence. Within-budget share is 0% with a positive observed denominator. BUILD_SPEC §5 clarified. |
| Q5 | Does CSV download mean only the current 50-row page or all matching listings? | Download all filtered detail-scoped rows, displayed columns only, quoted string IDs; label with row count. BUILD_SPEC §4 clarified. |
| Q6 | Does Compare inherit the global room-type multiselect? | Compare has its own exactly-one-room selector, independent of global Explore room/neighborhood selections; it inherits stay length, budget, reviews and sensitivity. BUILD_SPEC §2 clarified. |
| Q7 | Where does a selected-price map obtain pre-budget affordability values? Its original backend table had null budget fields, and its price_n was selected-population only. | Coordinator spotted the tooltip mismatch during cross-check; independent agent confirmed it. Backend now joins budget numerator/share and explicit pre_budget_price_n by neighborhood+room type, retaining selected price_n separately. BUILD_SPEC, DATA_CONTRACT and regression test updated. |
| Q8 | What is reviewed share when review counts are missing? Nullable Boolean.mean silently shrank the denominator, contrary to the spec. | Agent reproduced [1, missing] -> 100%, where selected-row definition requires 50%. Backend now counts observed positive reviews over all selected rows, preserving source nulls and separately reporting review_n. Added regression coverage; current source has no missing total review counts. |
| Q9 | What should be done when the local server cannot bind inside the sandbox? | Agent recorded the PermissionError and requested required escalation before starting localhost. This is an execution-environment issue, not a data/spec ambiguity. Browser testing was stopped when the user requested completion. |
| Q10 | How should offline geographic rendering work without a basemap/network? | Isolated implementation defaults to a labeled latitude/longitude grid, with optional online basemap. This is an implementation choice within the existing fallback requirement, not invented geographic boundaries. |

After reviewing the full 27-item record, BUILD_SPEC §4 also explicitly settled
authoritative detail-selection state/clearing, optional auto-tab navigation,
offline-first rendering, full-extent online-map fitting, small-population legend
exceptions, sorting before pagination, desktop-row/mobile-stack cards, and
rendered/downloadable methods contract. §6 distinguishes unseen-filter timings,
cache-hit timings and first-use environment setup. Prototype shortcomings in
these areas are not silently accepted as changes to product requirements.

## Changes made to the project

| File | Change |
|---|---|
| `../BUILD_SPEC.md` | v1.1: explicit dependencies, mixed-room KPI rules, comparison independence, neighborhood selection, export scope, selected/pre-budget empty states, and map tooltip fields. |
| `requirements-dashboard.txt` | Tested dashboard dependencies, separate from Phase 2's pandas-only environment. |
| `backend.py` | Correct map affordability join and reviewed-share denominator. Vectorized segment aggregation and reused summaries address the observed repeated-aggregation bottleneck. Public traveler metric definitions remain unchanged. |
| `test_backend.py` | Added map-population, missing-review-denominator and vectorized-vs-listing-formula regressions; 13 tests pass. |
| `DATA_CONTRACT.md` | Explicit selected-map versus pre-budget field semantics and missing-review share denominator. |
| `outputs/` | Regenerated summaries/maps and manifest from unchanged source; canonical listing rows/values preserved. |
| `README.md`, `READINESS.md`, notebook handoff text | Link to this review and distinguish completed independent review from remaining main-branch/team gates. |

The independent agent's own implementation changes and original findings are
preserved separately in the evidence directory. Machine-readable evidence:
[UI verification](fresh_agent_evidence/UI_VERIFICATION.json) and
[final backend verification](fresh_agent_evidence/FINAL_BACKEND_VERIFICATION.json).
No Phase 1 files were revised.

## Checks and evidence

- Original source remains 43,932 listings and the same SHA-256
  `16007ed61afb75ffe44a69e7296bd50a71d61b2cce7cf885eb9d71d1dbd6f289`.
- Independent agent ran the documented build and backend checks, then constructed
  an isolated Streamlit/Plotly interface using reusable backend functions.
- Streamlit AppTest covered 11 scenarios: default, budget250, empty selected with
  nonempty pre-budget data, empty neighborhoods, empty room types, reset,
  multiple room types, keyboard detail selection, all stays, sensitivity, and
  comparison behavior; see the raw UI verification artifact for exact labels.
- Final original backend check: `python -m phase2.test_backend` -> **13 tests,
  zero failures/errors**. Direct listing-level formulas cross-check vectorized
  segment results. A new process rebuilds and compares output hashes.
- UI timings before the final backend optimization: warm-font-cache cold app
  2.16s, cached rerun 0.193s; uncached budget 1.42s, multiroom 3.49s, all-stays
  4.99s and sensitivity 5.27s. Initial cold runs around 12s included temporary
  Matplotlib font-cache initialization. These are test-environment observations,
  not deployment promises. The subsequent vectorized optimization passed the
  data regressions; final UI performance was not re-certified.

## Remaining limits and submission steps

No unresolved core metric definition from this test remains in the spec. Final
Phase 3 browser checks remain: 375px/1280px layout, real mouse-hover/click,
network basemap failure, all-data map fit and scale-bar support. Automated
Streamlit tests do not prove pixel layout or actual browser interaction.

Team acceptance of reconciliation choices, committing/merging the canonical
package into `main`, and checking instructor access are still required. After
integration, rerun the documented checks against the submitted revision. No
grade, main-branch integration, or finished dashboard acceptance is claimed.
