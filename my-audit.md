# Module 9 Individual Audit — Yaxin Lyu

## Scope and version

Project: LA Airbnb Traveler Comparison Dashboard.

Version checked: supplied project-main.zip, archive comment
974233619d115337db6bc5bf599f354e66b1d224.
This identifies the reviewed archive, not the latest remote branch.

Feature: seven-night stay compatibility (U1), checked at the backend level.
Number: reviewed-listing share.

The supplied archive has no app.py. Therefore, I checked the backend
behavior, but could not complete the rendered user-interface audit.

## Intended user and requirements

A traveler planning a seven-night stay in an entire home/apt needs to
identify listings whose minimum stay fits the trip and understand how
many have review history.

BUILD_SPEC.md sections 2–3 require:
- Include listings with minimum_nights <= 7.
- Exclude unknown minimum stays when a specific trip length is active.
- Calculate reviewed share as listings with positive total reviews
  divided by ALL selected listings.

Reviewed share is a unitless proportion between 0 and 1, displayed
as a percentage. It is not a rating or quality score.

## Checks and results

I ran audit_check_yaxin.py in VS Code using Python 3.13.15 and pandas.

The default filters were all neighborhoods, Entire home/apt, seven
nights, no budget, minimum reviews 0, and high-price exclusion off.

| Check | Expected | Actual |
|---|---|---|
| Default selected population | Direct filter must match backend | Both selected 16,633 listings |
| Minimum stays [7, 8, missing] | Only the first row qualifies | Selected indexes: [0] |
| Reviewed share on selected data | 14,795 / 16,633 = 88.9497% | 88.9497% |
| Review counts [1, missing, 0] | 1 / 3 = 33.3% | 50.0% |

The full cleaned CSV contains 43,932 rows and zero missing total review
counts. Therefore, the missing-review defect does not affect the default
real-data result.

## Feature conclusion

The backend correctly handles the tested minimum-stay boundary:
seven nights qualifies, while eight nights and an unknown minimum
stay do not.

This supports a traveler's stay-length screening task. However,
minimum-stay compatibility does not confirm booking availability.

The sidebar, displayed count, listing table, and Reset behavior remain
untested because the reviewed archive does not include the App.

## Number finding and explanation

The missing-review case contains three selected listings:
one with a positive review count, one missing, and one with zero.

The required denominator is all three selected listings, so the
expected result is 1/3 = 33.3%.

overview_metrics() instead uses:

    d.number_of_reviews.gt(0).mean()

With nullable Int64 data, the comparison preserves the missing value,
and mean() skips it. This reduces the denominator to two and produces
1/2 = 50.0%, overstating the share by 16.7 percentage points.

For nonempty data, the calculation should count positive reviews
with missing comparisons filled as False and divide by len(d).
Source missing values should remain unchanged, review_n should be
disclosed separately, and empty data should still return N/A.

FRESH_AGENT_TEST.md Q8 says this was fixed, but the reviewed backend
still contains the expression above. The documentation and committed
implementation need to be reconciled.

## Reproduction

From the extracted project root, run:

    python audit_check_yaxin.py

The script directly filters the CSV and compares selected IDs with
filter_listings(). It independently counts positive reviews and divides
by all selected rows. It also constructs the two boundary cases.

The missing-review calculation can be reproduced separately with:

    import pandas as pd
    from phase2.backend import overview_metrics

    d = pd.read_csv(
        "phase2/outputs/listings.csv",
        dtype={"number_of_reviews": "Int64"}
    )
    case = d.head(3).copy().reset_index(drop=True)
    case["number_of_reviews"] = pd.Series(
        [1, pd.NA, 0], dtype="Int64"
    )
    print("Expected:", 1 / 3)
    print("Actual:", overview_metrics(case).iloc[0].reviewed_share)

Expected output: 0.3333333333333333.
Actual output on the reviewed backend: 0.5.

## Requested changes and remaining limits

CR-YL-01: Correct the reviewed-share denominator, add a missing-review
regression case, and reconcile FRESH_AGENT_TEST.md Q8 with the code.

CR-YL-02: Provide the accepted runnable team App so the seven-night
feature can be checked through its actual interface.

These requests are recorded in my local change-requests.md.
Their integration into the shared team repository is pending.

The checks establish backend behavior for the default population
and the stated small cases. They do not establish rendered UI behavior,
all filter combinations, or whether a newer version fixes the defect.

## Individual contribution and AI use

My audit focuses on stay compatibility and reviewed share, separately
from Xinyun Gu's map-hover and budget-share audit.

With AI assistance, I prepared and personally ran audit_check_yaxin.py
on my Mac and inspected its output. AI helped read the specification,
write the checks, explain the denominator issue, and draft this report.

I have not tested a live App, and I do not claim a teammate's checks
as my own. The rendered feature audit remains incomplete.