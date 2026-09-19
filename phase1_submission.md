# Phase 1 Project Submission

## DSO 576 | Python and Agentic Coding for Business Analytics

Note: We switched our topic from Amazon reviews to a short-term rental marketplace for Los Angeles, and the dashboard focuses on helping users compare neighborhoods, prices, and availability for booking or listing decisions.

### 1 Establish the data fit

Open a manageable real sample of the data and use pandas to explore it. The dataset I opened is the public Airbnb listings file for the Los Angeles market, stored in the workspace as `listings.csv` and available from the public Inside Airbnb archive: https://insideairbnb.com/get-the-data/

#### Source and scope
- Source: Inside Airbnb public listing dataset for Los Angeles / surrounding metro neighborhoods.
- What I opened: the full listing table from `listings.csv`.
- One row represents one Airbnb listing record for a single property in the Los Angeles area.
- Sample size and coverage: 43,932 rows and 19 columns. The file is about 21.9 MB in memory; the dataset covers many neighborhoods in Los Angeles County, including Hollywood, Venice, Santa Monica, Downtown, Long Beach, Pasadena, Beverly Hills, and surrounding areas. It is a static market snapshot rather than a time series, so it captures cross-sectional variation across listings.
- Relevant market scope: each listing includes location, price, room type, occupancy proxy, and review activity, which is enough to benchmark market conditions and compare neighborhoods.

#### Relevant columns

| Column and source table | What it contains | How we will use it |
|---|---|---|
| `neighbourhood` in listings | Neighborhood name for each listing | Let the user filter by area and compare local pricing and demand. |
| `room_type` in listings | Entire home/apartment, private room, hotel room, or shared room | Compare market segments and support booking-type decisions. |
| `price` in listings | Nightly price in USD | Main comparison metric and the key filter for affordability. |
| `availability_365` in listings | Number of nights available in the next 365 days | Proxy for occupancy and demand; spot low-availability or high-demand areas. |
| `number_of_reviews` in listings | Total review count | Measure listing traction and social proof. |
| `reviews_per_month` in listings | Average monthly reviews | Gauge recent demand and recency of activity. |
| `latitude` and `longitude` in listings | Geographic coordinates | Show map-based distribution and neighborhood comparisons. |
| `minimum_nights` in listings | Minimum stay requirement | Help users understand booking flexibility and host expectations. |
| `host_name` / `host_id` in listings | Host identifier and listing owner | Useful for detecting repeated host inventory and market concentration. |

#### What the data can support
The available data supports a practical decision dashboard for prospective travelers and Airbnb hosts. The product can help users answer questions such as:
- Which neighborhoods offer the best balance of price, review activity, and availability?
- How do different property types compare in the same area?
- Where are the best opportunities for a host to list a property at a competitive price?
- Which neighborhoods appear to have strong occupancy and enough customer activity to justify a listing?

With this dataset, a website or dashboard could support:
- Neighborhood and room-type filters
- A price-vs-availability scatterplot
- Average price by neighborhood
- A market summary table ranked by demand and value
- A map view with listing density and average nightly rate
- A shortlist for hosts or travelers based on affordability, occupancy, and review volume

The core feasible use case is a market comparison and decision-support dashboard for choosing a listing strategy or a purchase/rental opportunity in Los Angeles. The dashboard can help a user identify which neighborhoods and property types seem most attractive for either booking or listing.

Important missing information:
- Calendar-level booking demand by date and seasonality; we do not have actual occupancy over time.
- Amenities, cancellation policy, and guest ratings; those are not in this table.
- Host response time and listing photos, which matter for converting bookings.
- Review text sentiment, listing quality, and exact booking conversion data.

How to address these gaps:
- Add a calendar or availability source for nightly demand and seasonal patterns.
- Merge with a listing-details dataset for amenities and policies.
- Add a review dataset for sentiment and common guest complaints.
- For a smaller initial scope, focus only on neighborhood, room type, price, availability, and review volume; that is already enough to deliver a strong first version of the dashboard.

### 2 Sketch the dashboard

Below is a low-fidelity dashboard sketch showing the main user flow and decision support.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ Airbnb Market Decision Dashboard                  Los Angeles Market Snapshot │
├───────────────────────────────────────────────────────────────────────────────┤
│ Left sidebar filters                                                        │
│ • Price range: $50–$500                                                    │
│ • Availability: 0–365                                                      │
│ • Minimum nights: 1–30                                                     │
│ • Review count: 0–500                                                      │
│ • Sort by: Avg price, Occupancy, Review volume                             │
│                                                                            │
│ Main area                                                                  │
│ Top KPI cards:                                                              │
│ 1) Avg nightly price: $224                                                  │
│ 2) Listings with 90+ days available: 31%                                   │
│ 3) Avg reviews/month: 1.4                                                 │
│ 4) Top neighborhood by demand: Hollywood                                   │
│                                                                            │
│ ┌─────────────────────┐   ┌──────────────────────────────────────────────┐  │
│ │ Avg price by        │   │ Availability vs price                          │  │
│ │ neighborhood        │   │ scatterplot                                    │  │
│ │ (bar chart)         │   │ color = neighborhood                           │  │
│ └─────────────────────┘   └──────────────────────────────────────────────┘  │
│                                                                            │
│ ┌───────────────────────────────────────────────┐                           │
│ │ Top candidate neighborhoods                   │                           │
│ │ Neighborhood   Avg Price   Avail.   Reviews/mo │                           │
│ │ Hollywood     $198        140d      1.8       │                           │
│ │ Venice        $260        110d      1.4       │                           │
│ │ Long Beach    $175        180d      1.2       │                           │
│ └───────────────────────────────────────────────┘                           │
│                                                                            │
│ ┌───────────────────────────────────────────────┐                           │
│ │ Map view                                     │                           │
│ │ [listing density + price hotspots]            │                           │
│ └───────────────────────────────────────────────┘                           │
│                                                                            │
│ Decision help:                                                              │
│ “For a traveler with a $200 budget, Hollywood and Long Beach show the best │
│ value-to-demand tradeoff; for a host, Venice has high price potential but  │
│ stronger competition.”                                                      │
└───────────────────────────────────────────────────────────────────────────────┘
```

#### What the user would see and do
- The user selects a neighborhood, room type, and price range from the filter panel.
- The charts and table update immediately to show market conditions in the chosen segment.
- The user can compare two neighborhoods or filter to one property type to decide where to book or list.
- The dashboard shows the action or decision the user can take: choose a value area, target a market segment, or decide whether a listing is competitively priced.

#### Mapping the sketch to the data
- `neighbourhood` and `room_type` drive the sidebar filters.
- `price` determines affordability thresholds and average-price charts.
- `availability_365` powers the occupancy/demand signal and the scatterplot.
- `reviews_per_month` and `number_of_reviews` help the user judge social proof and recent demand.
- `latitude` and `longitude` support the map-based view.
- Derived metric: “value score” = normalized combination of lower price, higher availability, and stronger review activity.

This dashboard concept is feasible with the available data and gives a clear first version of the product, while the missing fields can be handled with a later data-merge step or a narrowed initial scope.

Repo link: https://github.com/cynthiaqgao/project
