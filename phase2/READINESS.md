# Phase 2 rubric evidence and submission gates

Target: 3/3 on each of nine criteria. Scores belong to the grader; this matrix
records evidence and remaining gates rather than asserting an earned 27/27.

| Criterion | Evidence targeting 3 points | Remaining gate |
|---|---|---|
| 1. Revised vision | BUILD_SPEC §1: specific traveler, shortlist decision, improvement, four select -> see -> decide use cases | Review traveler scope |
| 2. Plan serves vision | Every major view mapped to U1–U4, no host metrics or orphan features | Preserve mapping during UI build |
| 3. Dashboard specification | Defaults, tabs, controls, formulas, legends, scales, map hover/click, selection/reset, empty/small-group behavior | UI visual checks occur in Phase 3 |
| 4. Architecture | Separate canonical cleaning, build, pure backend, tests and future view layer with explicit inputs/outputs | Keep UI formulas out of metrics |
| 5. Technical design | Local pandas/CSV scale, explicit loading, cache invalidation, map aggregation, pagination, deployment paths and performance targets | Measure actual Phase 3 responsiveness |
| 6. Grounded in data | Full-source inspection, audit/types/missingness, preserved IDs/numerics, branch reconciliation and one canonical dataset | Team review/acceptance and merge to main remain required |
| 7. Analysis backend | Reusable filtering, KPI, affordability, ranking, CDF, map and comparison functions; automated independent checks | See actual verification.json result |
| 8. Complete | Data contract, executable run path, deterministic outputs, fresh-process rerun and independent fresh-agent build/test; see FRESH_AGENT_TEST.md | Rerun on submitted main revision; Phase 3 browser acceptance remains separate |
| 9. Clear & succinct spec | Big picture first, compact use-case/metric/view/architecture tables; implementations live outside spec | Fresh-agent feedback may identify cuts or clarifications |

## Before submission

1. Record team acceptance of reconciliation choices and merge canonical data,
   BUILD_SPEC and backend into main. Current files alone do not satisfy “on main.”
2. Run build and tests on the merged main revision; commit canonical CSV and
   reproducibility artifacts using the scoped ignore exceptions.
3. Independent context-isolated agent build/test completed on the working
   repository snapshot. Questions, assumptions, fixes and limits are recorded
   in `FRESH_AGENT_TEST.md`. Preserve the evidence and rerun checks on submitted
   main; this review is distinct from backend subprocess verification.
4. Ensure README/run links point to the merged revision and confirm instructor
   access. Do not submit historical individual-cleaning artifacts as Phase 2.

The dashboard interface, responsive layout, live hover interaction and actual
performance measurements are Phase 3 work; Phase 2 specifies their checks and
provides reusable analysis. No synthetic temporal or bedroom/bathroom data was
added to satisfy a chart preference.
