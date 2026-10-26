# Change requests

## Claims

| Person | Feature | Number | Evidence contributed |
|---|---|---|---|
| Yaxin Lyu | Seven-night stay compatibility (U1), checked at backend level | Reviewed-listing share | Direct calculation on the cleaned CSV, a minimum-stay boundary case, and a nullable missing-review case. Rendered UI remains untested because the supplied archive has no app.py. |

## CR-YL-01 — Correct reviewed-share denominator when reviews are missing

- **Status:** Open.
- **Version checked:** Supplied project-main.zip, archive comment 974233619d115337db6bc5bf599f354e66b1d224.
- **Requirement:** BUILD_SPEC.md section 3 defines reviewed share as selected listings with positive total reviews divided by ALL selected listings.
- **Finding:** With nullable Int64 review counts [1, missing, 0], the expected share is 1/3 = 33.3%, but overview_metrics() returns 50.0%.
- **Cause:** number_of_reviews.gt(0).mean() skips the missing value and divides by two observed entries rather than three selected rows.
- **Requested change:** For nonempty data, count positive reviews with missing comparisons filled as False, then divide by the total selected row count. Preserve source missing values, disclose review_n separately, and retain N/A for an empty population.
- **Regression check:** [1, missing, 0] must return 1/3; empty input must return N/A.
- **Documentation:** FRESH_AGENT_TEST.md Q8 describes this as fixed, but the reviewed backend still contains the faulty expression. Reconcile the document with the committed code.
- **Actual-data impact:** The supplied CSV has no missing total review counts. Under default filters, 14,795 of 16,633 selected listings have reviews; direct and backend calculations both return 88.9497%. The defect does not change this default result.
- **Evidence:** audit_check_yaxin.py, personally run in VS Code using Python 3.13.15.

## CR-YL-02 — Provide the runnable App for user-facing verification

- **Status:** Open.
- **Finding:** The reviewed archive contains backend code and cleaned data but no app.py. The seven-night filter can be checked in code, but its user-facing controls cannot be tested from this archive.
- **Backend evidence:** Default filters select 16,633 listings. A boundary case with minimum stays [7, 8, missing] selects only the first row, as required.
- **Requested change:** Provide the accepted team App version and startup dependencies or its accessible running URL.
- **Follow-up check:** As a traveler, select Entire home/apt and seven nights; compare the displayed count with the backend, inspect minimum-stay compatibility, and test Reset.
- **Limit:** Sidebar behavior, rendered results, and Reset have not been verified.