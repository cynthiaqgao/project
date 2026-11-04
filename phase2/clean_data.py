"""Canonical project cleaning. Run from the repository: python -m phase2.build."""
from pathlib import Path
import hashlib
import re
import unicodedata
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IDS = ['id', 'host_id', 'host_profile_id']
COUNTS = ['minimum_nights', 'number_of_reviews', 'calculated_host_listings_count',
          'availability_365', 'number_of_reviews_ltm']
FLOATS = ['price', 'reviews_per_month', 'latitude', 'longitude']
TEXT = ['name', 'host_name', 'neighbourhood_group', 'neighbourhood', 'room_type', 'license']
SOURCE_COLUMNS = ['id', 'name', 'host_id', 'host_profile_id', 'host_name',
                  'neighbourhood_group', 'neighbourhood', 'latitude', 'longitude',
                  'room_type', 'price', 'minimum_nights', 'number_of_reviews',
                  'last_review', 'reviews_per_month', 'calculated_host_listings_count',
                  'availability_365', 'number_of_reviews_ltm', 'license']
ROOMS = ['Entire home/apt', 'Private room', 'Shared room', 'Hotel room']
BOOLS = ['price_missing', 'minimum_nights_missing', 'never_reviewed',
         'review_fields_inconsistent', 'review_counts_inconsistent',
         'price_high_outlier', 'price_under_10', 'minimum_nights_over_365',
         'coordinate_review', 'license_missing', 'room_type_unrecognized']

def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def normalize(value):
    if pd.isna(value):
        return pd.NA
    value = ''.join(c for c in value if unicodedata.category(c) != 'Cf')
    return re.sub(r'\s+', ' ', value).strip() or pd.NA

def exact_float(values):
    """Correctly rounded parse (Python float), identical on every platform/pandas build."""
    return pd.array([float(v) if pd.notna(v) else pd.NA for v in values], dtype='Float64')

def clean_listings(raw):
    """Return (canonical dataframe, audit); never silently choose duplicate IDs."""
    if list(raw.columns) != SOURCE_COLUMNS:
        raise ValueError('Source schema changed; review the data contract before rebuilding.')
    if any(str(raw[c].dtype) != 'string' for c in IDS):
        raise ValueError('Load raw CSV with dtype="string" to protect identifier precision.')
    d = raw.copy()
    for c in d:
        d[c] = d[c].str.strip().replace('', pd.NA)
    for c in TEXT:
        d[c] = d[c].map(normalize).astype('string')
    d['license'] = d.license.replace('N/A', pd.NA)
    exact_duplicates = int(d.duplicated().sum())
    d = d.drop_duplicates().reset_index(drop=True)
    if d.id.isna().any() or d.id.duplicated().any():
        raise ValueError('Missing/conflicting listing IDs require source investigation.')
    for c in IDS:
        if (d[c].notna() & ~d[c].str.fullmatch(r'\d+', na=False)).any():
            raise ValueError(f'Invalid identifier: {c}')
    for c in COUNTS + FLOATS:
        n = pd.to_numeric(d[c], errors='coerce')
        if (d[c].notna() & n.isna()).any():
            raise ValueError(f'Unparseable numeric value: {c}')
        if c in COUNTS:
            invalid = n.notna() & ((n < 0) | (n % 1 != 0))
            if c in ['minimum_nights', 'calculated_host_listings_count']:
                invalid |= n.notna() & n.lt(1)
        elif c == 'latitude':
            invalid = n.notna() & ~n.between(-90, 90)
        elif c == 'longitude':
            invalid = n.notna() & ~n.between(-180, 180)
        else:
            invalid = n.notna() & n.lt(0)
            if c == 'price':
                invalid |= n.eq(0)
        if c == 'availability_365':
            invalid |= n.gt(365)
        if invalid.any():
            raise ValueError(f'Invalid {c}: {int(invalid.sum())} rows; investigate, do not delete.')
        d[c] = n.astype('Int64') if c in COUNTS else exact_float(d[c])
    dates = pd.to_datetime(d.last_review, format='%Y-%m-%d', errors='coerce')
    if (d.last_review.notna() & (dates.isna() | ~d.last_review.str.fullmatch(r'\d{4}-\d{2}-\d{2}', na=False))).any():
        raise ValueError('Invalid review dates; investigate before proceeding.')
    # No scrape date is known. Do not substitute max(last_review) or machine time.
    d['last_review'] = dates.dt.strftime('%Y-%m-%d').astype('string')
    for c in ['neighbourhood_group', 'neighbourhood', 'room_type']:
        d[c] = d[c].fillna('Unknown')
    d['price_missing'] = d.price.isna()
    d['minimum_nights_missing'] = d.minimum_nights.isna()
    d['never_reviewed'] = d.number_of_reviews.eq(0).fillna(False)
    d['review_fields_inconsistent'] = ((d.never_reviewed & (d.last_review.notna() | d.reviews_per_month.notna())) |
        (~d.never_reviewed & (d.last_review.isna() | d.reviews_per_month.isna()))).fillna(False)
    d['review_counts_inconsistent'] = d.number_of_reviews_ltm.gt(d.number_of_reviews).fillna(False)
    q1, q3 = d.price.quantile([.25, .75])
    threshold = float(q3 + 3 * (q3 - q1))
    d['price_high_outlier'] = d.price.gt(threshold).fillna(False)
    d['price_under_10'] = d.price.lt(10).fillna(False)
    d['minimum_nights_over_365'] = d.minimum_nights.gt(365).fillna(False)
    d['coordinate_review'] = ~(d.latitude.between(33, 35) & d.longitude.between(-119, -117)).fillna(False)
    d['license_missing'] = d.license.isna()
    d['room_type_unrecognized'] = ~d.room_type.isin(ROOMS)
    for c in BOOLS:
        d[c] = d[c].astype(bool)
    d['license_status'] = pd.Series('Reported; unverified', index=d.index, dtype='string')
    d.loc[d.license.str.match(r'(?i)^exempt\b', na=False), 'license_status'] = 'Exemption claimed; unverified'
    d.loc[d.license_missing, 'license_status'] = 'Unknown'
    audit = {
        'input_rows': len(raw), 'output_rows': len(d), 'exact_duplicates_removed': exact_duplicates,
        'grain': 'One listing per id in one snapshot; snapshot date unknown',
        'numeric_failures': 0, 'missing': d.isna().sum().astype(int).to_dict(),
        'text_changes': {c: int(raw[c].fillna('').ne(d[c].fillna('')).sum()) for c in TEXT},
        'flags': {c: int(d[c].sum()) for c in BOOLS},
        'high_price_threshold_usd': threshold,
        'last_review_range': [d.last_review.min(), d.last_review.max()],
        'room_type_counts': d.room_type.value_counts().to_dict(),
        'dtypes': {c: str(t) for c, t in d.dtypes.items()},
    }
    return d, audit

def load_listings(path=ROOT / 'phase2/outputs/listings.csv'):
    """Load the canonical CSV without losing ID digits or interpreting False as truthy."""
    d = pd.read_csv(path, dtype='string', keep_default_na=False).replace('', pd.NA)
    for c in COUNTS:
        d[c] = pd.to_numeric(d[c], errors='raise').astype('Int64')
    for c in FLOATS:
        d[c] = exact_float(d[c])
    for c in BOOLS:
        if not d[c].isin(['True', 'False']).all():
            raise ValueError(f'Invalid serialized flag: {c}')
        d[c] = d[c].map({'True': True, 'False': False}).astype(bool)
    if d.id.isna().any() or not d.id.is_unique:
        raise ValueError('Canonical dataset violates listing grain.')
    return d
