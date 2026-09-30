# Phase 1 Project Submission: Amazon Fashion Review Analysis

## 1. Establish the data fit

### Source and scope

The source is the [Amazon Reviews 2023 dataset](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023), specifically the Amazon Fashion review file `Amazon_Fashion.jsonl`. The JSONL file contains one JSON object per line. One row represents one customer's review of an Amazon Fashion product.

The local file is approximately 1.0 GB and contains 2,500,939 review rows. To make the initial exploration manageable and reproducible, `phase1_jsonl_analysis.py` reads the first 25,000 rows with `pandas.read_json(..., lines=True, nrows=25000)`. The sample covers reviews dated from 2002-05-07 through 2023-09-11, 25,000 review rows, 22,974 products, and 24,891 reviewers. In the complete file, pandas reports 825,869 products and 2,035,490 reviewers.

The complete-file check found an average rating of 4.13, 93.5% verified purchases, and this rating distribution: 1 star 303,411; 2 stars 173,462; 3 stars 245,471; 4 stars 352,327; and 5 stars 1,426,268. These figures describe the supplied dataset and should not be interpreted as representative of all fashion purchases.

### Relevant columns

| Column and source file | What it contains | How we will use it |
|---|---|---|
| `rating` in `Amazon_Fashion.jsonl` | Customer rating from 1 to 5 | Filter products by satisfaction and compare positive versus negative reviews. |
| `title` in `Amazon_Fashion.jsonl` | Short review headline | Display representative review summaries and search for recurring concerns. |
| `text` in `Amazon_Fashion.jsonl` | Full customer review text | Identify repeated needs, complaints, and product attributes with keyword or text analysis. |
| `parent_asin` in `Amazon_Fashion.jsonl` | Product-family identifier | Group reviews to rank products and compare review patterns. |
| `asin` in `Amazon_Fashion.jsonl` | Specific item identifier | Preserve item-level detail when a product family has variants. |
| `timestamp` in `Amazon_Fashion.jsonl` | Review time in Unix milliseconds | Convert to a date and examine whether concerns change over time. |
| `helpful_vote` in `Amazon_Fashion.jsonl` | Number of helpful votes | Prioritize reviews that other shoppers found useful. |
| `verified_purchase` in `Amazon_Fashion.jsonl` | Whether the review is marked as a verified purchase | Compare verified and unverified review patterns and qualify confidence. |

### What the data can support

The data can support a static or interactive review-insights dashboard for a marketing or product manager. The user could select a product or product family, rating range, date range, and verified-purchase status. The dashboard could show review volume, average rating, rating distribution, helpful-vote-weighted examples, and recurring words or themes in positive and negative reviews. These outputs could help decide which customer concerns or attributes deserve stronger product information or marketing emphasis.

The data cannot, by itself, establish causal reasons for sales, profit, conversion, returns, inventory, price changes, product attributes, or whether a review is truthful. It also does not provide product descriptions, structured fashion attributes, prices, or bought-together relationships in this file. A later phase should join an Amazon product-metadata file using `parent_asin`, add price and sales or conversion data if available, and treat text themes as signals for investigation rather than proof of demand. The high five-star share and possible review-selection bias are additional limitations.

## 2. Dashboard sketch

### Main screen layout

**Header:** “Amazon Fashion Review Signals” with a short decision prompt: *Which product concerns or attributes should we prioritize?*

**Filters:**

- Product family: `All products`, plus example `parent_asin` values from the selected sample.
- Rating: `All`, `1–2 stars`, `3 stars`, `4–5 stars`.
- Review date: start and end date, based on converted `timestamp`.
- Purchase status: `All`, `Verified`, `Unverified`.
- Search phrase: searches `title` and `text` for an attribute or concern such as “size”, “fit”, “quality”, or “color”.

When a filter changes, the metric cards, charts, ranked concern terms, and review table update to the filtered review population. Any illustrative values in the sketch should be labeled **illustrative only** until the dashboard is connected to the selected dataset.

**Metric cards:** review count (`parent_asin` / row count), average rating (`rating`), verified-purchase percentage (`verified_purchase`), and median helpful votes (`helpful_vote`). These establish whether the selected product or concern has enough review evidence to act on.

**Charts:**

- Rating distribution: helps identify whether dissatisfaction is concentrated in one product or spread across products.
- Review volume over time: uses `timestamp` and shows whether a concern is recent or persistent.
- Positive versus negative concern terms: uses `rating`, `title`, and `text` to compare what customers praise and criticize.

**Review evidence table:** shows `parent_asin`, `rating`, `title`, a shortened `text`, `helpful_vote`, `verified_purchase`, and review date. This lets the decision-maker inspect the original evidence before prioritizing a product change or marketing claim.

**Decision annotation:** a highlighted section ranks candidate priorities using review frequency, negative-rating share, and helpful votes. It should say “signal for investigation,” not “proven customer requirement,” because this JSONL lacks sales, product-attribute, and causal data.

**Repository/code:** The reproducible exploration code is `phase1_jsonl_analysis.py` in the private team repository. The project source is the Amazon Reviews 2023 dataset linked above.