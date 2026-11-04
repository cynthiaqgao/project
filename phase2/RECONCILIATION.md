# Team cleaning reconciliation for Phase 2

Prepared from local source inspection and fetched team branches on October 15,
2026. These are implemented proposed canonical resolutions; no team agreement is
claimed without review. This project package supersedes earlier individual
cleaning outputs **for Phase 2 only**.

## Inspected evidence

| Branch and inspected revision | Evidence inspected |
|---|---|
| Kyi-branch `e5c9eff` | Source-preserving cleaner/verification; nullable rates; high-price flags |
| Cynthia_branch `f06c9ae` | `cynthia_hw6.py`: Unicode/text normalization, structural zero-rate fill, percentile flags |
| cleaning-hongjie `6dcc257` | `clean_listings.py` and README: string IDs, missing values retained, no row deletions |
| cleaning-yaxin `4dbd197` | `clean_listings_yaxin.py`: missing-price retention and >$1,000 review flag |
| Warner `8299b28` | Rules/README: alternate source hash, null retention, zero-review rate fill, 99th-percentile flags |
| phase2-sariel `a94648d` | `cleaning.py` and `test_backend.py`: 38,353-row priced-only population, zero-fill rates, reusable aggregations |

Inspection did not execute team scripts containing machine-specific paths.
Source scripts are evidence of prior choices, not instructions to overwrite this
project's source. Remote main currently contains Phase 1; no Airbnb build spec
was found in the fetched project branches. The unrelated wildfire BUILD_SPEC in
the parent coursework directory is not an Airbnb specification.

## Conflicts and implemented resolutions

| Issue | Conflict | Canonical decision and traveler rationale |
|---|---|---|
| Source version | Warner documents hash `d3b34461d0dc409dbe9f99573e3343e342dbcefbb0767b4b62d60b3beb4aceb2`, different from project source | Pin project `LA_listings.csv` hash `16007ed6…d6f289`; never union snapshots or import another file's date. |
| Listing population | Backend drops missing price/minimum stay, yielding 38,353 rows | Keep all 43,932 listings. Active traveler filters exclude unknown values as specified; metric denominators are explicit. This preserves inventory evidence and reveals missingness. |
| IDs | Default CSV inference can round host identifiers | All fields initially loaded as strings; exact identifier digits checked after serialization. |
| Duplicates | Backend silently keeps first listing ID | Remove only exact repeated rows; fail on conflicting IDs. Current source has none. Repeated hosts retained. |
| Missing monthly review rate | Some branches fill with 0, others retain null | Retain 11,311 null rates. A lifetime count of zero does not establish a comparable exposure-normalized rate. Use true review counts, including zeros, for primary traveler review evidence. |
| Extreme price | Fixed >$1,000 vs 99th/room-percentile vs 3-IQR flags | Retain all positive prices. Primary median/IQR; one fixed global Q3+3IQR flag for explicit sensitivity. Source threshold $1,276. No branch-specific flag drives hidden exclusion. |
| Text | Outer trimming vs removal of invisible formatting | Remove Cf formatting, normalize whitespace, preserve meaning/case/accents. Canonical labels from source; no fabricated aliases. |
| Minimum stay | <=30-night analytical cut vs all records | Store raw minimum nights. Traveler-specific filter minimum_nights<=planned nights (default7); not a legal short-term-rental definition. |
| Missing license | Blank vs literal N/A vs inferred licensing | Normalize blank/N/A to null; no legality inference. Not a traveler ranking metric. |
| Dates | Review maximum treated as scrape proxy in some work | Preserve valid review dates; collection date unknown. No seasonality/MoM/YoY claims. |
| Availability | Phase 1 mentions occupancy/demand | Phase 2 revises interpretation only: annual calendar context, not actual occupancy or confirmation for a trip. Phase 1 files remain untouched. |
| Vision | Host/location opportunity analyses appear in team work | Traveler shortlist: affordability, minimum-stay compatibility, like-for-like prices, review evidence and geographic context. No revenue or recruitment score. |

## Integration handoff

Review this table as a team, record decisions/reviewer/date, then integrate
`BUILD_SPEC.md`, `phase2/` and the scoped `.gitignore` additions into main. The
canonical dataset must be committed, not just generated locally. Existing raw
source is already tracked; keep it immutable. Run the documented build/tests on
main and compare manifest hashes. Do not copy earlier 38,353-row assertions into
the new backend tests. This work has not merged or pushed main, and has not
claimed other members approved the resolutions.
