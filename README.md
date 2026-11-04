# Phase 3: LA Stay Shortlist, a Los Angeles Airbnb traveler dashboard

DSO 576 team project, Phase 3 MVP. A Streamlit dashboard that helps a traveler plan a Los Angeles stay
using Inside Airbnb listing data.

| | Link |
|---|---|
| Live app | _add the Streamlit Community Cloud URL_ |
| Demo video | _add the video link_ |
| Repository | https://github.com/cynthiaqgao/project (branch `main`) |

## Intended users and decisions

**User:** a traveler planning a Los Angeles trip who doesn't know the city's neighborhoods well.

**Decision:** which neighborhoods and room types to shortlist for a given nightly budget and stay length,
before checking live prices and availability on Airbnb.

| Page | Question it answers |
|---|---|
| Explore | How many places fit my filters, what's the typical nightly price, and which neighborhoods are cheapest or have the most places within my budget? Where are they on the map, and how far are they from Downtown, the beach and LAX? |
| Compare neighborhoods | For one room type, how do two neighborhoods compare on price, budget fit and review history? |
| Listings & methods | Which individual places should I open on Airbnb, and how is each number calculated? |

Filters: neighborhoods, room type, stay length (nights), nightly budget (slider), minimum reviews, and
"hide unusually high prices". Clicking a map bubble or table row spotlights that neighborhood, with
links to a live Airbnb search.

## Run locally

Requires Python 3.10+. From the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Then open http://localhost:8501. If `phase2/outputs/listings.csv` is missing, rebuild it with
`python -m phase2.build`. Run the backend checks with `python -m phase2.test_backend`.

Entry file `app.py`; page views in `views/`; metric logic in `phase2/backend.py`; theme in
`.streamlit/config.toml`.

## Data scope

- **Source:** Inside Airbnb, Los Angeles listings (`LA_listings.csv`, CC BY 4.0), one snapshot.
- **Coverage:** all 43,932 listings in 265 neighborhoods and 4 room types.
  **No subset or sample is used.** The app reads the full cleaned file `phase2/outputs/listings.csv`.
- **Cleaning:** no rows removed. 5,570 listings without a price stay in counts but are left out of price
  statistics (never imputed). Unusually high prices (above Q3 + 3×IQR) are flagged, not deleted.
- **Map:** neighborhood bubbles sit at the average coordinates of their listings. Distances are
  straight-line miles. Street and USA map backgrounds load from OpenStreetMap/CARTO and need internet.

## Current limitations

- **Prices are listed nightly rates, not quotes.** Cleaning fees, Airbnb service fees and occupancy taxes
  are not included, and the snapshot date is unknown, so prices may have changed.
- **No dates or seasons.** The data is a single snapshot, so the app cannot show seasonal or month-by-month prices.
- **No ratings, bedrooms or guest capacity.** Review counts show stay history, not quality. Room type is not bedrooms.
- **Availability is not occupancy.** "Open nights per year" is the host calendar in the source window, not bookings.
- **Small neighborhoods are not ranked.** Price and budget rankings need at least 30 priced listings per
  neighborhood; smaller ones still appear on the map and in the table.
- **Distances are as the crow flies,** not driving or transit time.

## More documentation

- `BUILD_SPEC.md`: dashboard specification and metric definitions
- `phase2/DATA_CONTRACT.md`: canonical data fields and rules
- `DASHBOARD_SHARING.md`: deployment and sharing steps
