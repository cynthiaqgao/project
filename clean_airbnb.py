"""Deterministic, conservative cleaning of the supplied LA Airbnb snapshot."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import pandas as pd

ROOT = Path(__file__).resolve().parent
IDS = ['id', 'host_id', 'host_profile_id']
COUNTS = ['minimum_nights', 'number_of_reviews', 'calculated_host_listings_count',
          'availability_365', 'number_of_reviews_ltm']
NUMBERS = COUNTS + ['price', 'reviews_per_month', 'latitude', 'longitude']
TEXT = ['name', 'host_name', 'neighbourhood_group', 'neighbourhood', 'room_type', 'license']

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def clean(source=ROOT/'LA_listings.csv', output=ROOT/'outputs'):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    backup = ROOT/'raw_backup'/source.name
    backup.parent.mkdir(exist_ok=True)
    original_hash = sha(source)
    if backup.exists():
        if sha(backup) != original_hash:
            raise ValueError('Backup differs: do not overwrite an earlier source version.')
    else:
        shutil.copy2(source, backup)
    assert sha(backup) == original_hash
    # Load EVERY field as text: floating point would corrupt large identifiers.
    raw = pd.read_csv(source, dtype='string', keep_default_na=False)
    d = raw.copy()
    missing_before = {c: int(raw[c].str.strip().eq('').sum()) for c in raw}
    license_na_markers = int(raw.license.str.strip().eq('N/A').sum())
    missing_before['license'] += license_na_markers
    for c in d:
        d[c] = d[c].str.strip().replace('', pd.NA)
    d['license'] = d.license.replace('N/A', pd.NA)
    text_changes = {c: int((raw[c] != d[c].fillna('')).sum()) for c in TEXT}
    exact_duplicates = int(raw.duplicated().sum())
    d = d.loc[~raw.duplicated()].copy()
    repeated_ids = int(d['id'].duplicated(keep=False).sum())
    if repeated_ids or d.id.isna().any():
        raise ValueError('Conflicting/missing listing keys require investigation; no arbitrary removal.')
    id_failures = {c: int((d[c].notna() & ~d[c].str.fullmatch(r'\d+', na=False)).sum()) for c in IDS}
    if any(id_failures.values()):
        raise ValueError('Identifiers must be digit strings; preserve their original precision.')
    failed, invalid = {}, {}
    for c in NUMBERS:
        n = pd.to_numeric(d[c], errors='coerce')
        failed[c] = int((d[c].notna() & n.isna()).sum())
        bad = n.notna() & (n < 0)
        if c == 'price': bad = n.notna() & (n <= 0)
        if c in ['minimum_nights', 'calculated_host_listings_count']:
            bad |= n.notna() & (n < 1)
        if c in COUNTS: bad |= n.notna() & (n % 1 != 0)
        if c == 'availability_365': bad |= n > 365
        if c == 'latitude': bad = n.notna() & ~n.between(-90, 90)
        if c == 'longitude': bad = n.notna() & ~n.between(-180, 180)
        invalid[c] = int(bad.sum())
        n = n.mask(bad)
        d[c] = n.astype('Int64' if c in COUNTS else 'Float64')
    dates = pd.to_datetime(d.last_review, format='%Y-%m-%d', errors='coerce')
    failed['last_review'] = int((d.last_review.notna() & dates.isna()).sum())
    invalid['future_last_review'] = int((dates > pd.Timestamp('2026-10-02')).sum())
    dates = dates.mask(dates > pd.Timestamp('2026-10-02'))
    d['last_review'] = dates.dt.strftime('%Y-%m-%d').astype('string')
    unknown_groups = {}
    for c in ['neighbourhood', 'neighbourhood_group', 'room_type']:
        unknown_groups[c] = int(d[c].isna().sum())
        d[c] = d[c].fillna('Unknown')
    known_rooms = ['Entire home/apt', 'Private room', 'Shared room', 'Hotel room', 'Unknown']
    d['room_type_unrecognized'] = ~d.room_type.isin(known_rooms)
    d['license_missing'] = d.license.isna()
    d['license_status'] = pd.Series('License provided', index=d.index, dtype='string')
    d.loc[d.license.str.match(r'(?i)^exempt\b', na=False), 'license_status'] = 'Exemption claimed'
    d.loc[d.license_missing, 'license_status'] = 'Missing'
    d['price_missing'] = d.price.isna()
    d['no_reviews'] = d.number_of_reviews.eq(0)
    # Review rate remains null for never-reviewed listings; no assumption about exposure time.
    d['review_fields_inconsistent'] = ((d.no_reviews & (d.last_review.notna() | d.reviews_per_month.notna())) |
                                       (~d.no_reviews & (d.last_review.isna() | d.reviews_per_month.isna())))
    d['review_counts_inconsistent'] = d.number_of_reviews_ltm.gt(d.number_of_reviews)
    q1, q3 = d.price.quantile([.25, .75])
    upper = float(q3 + 3*(q3-q1))
    d['price_high_outlier'] = d.price.gt(upper).fillna(False)
    d['price_under_10'] = d.price.lt(10).fillna(False)
    d['minimum_nights_over_365'] = d.minimum_nights.gt(365).fillna(False)
    d['short_stay_eligible'] = d.minimum_nights.le(30).fillna(False)
    d['short_stay_price_eligible'] = d.short_stay_eligible & d.price.notna()
    # Wide metro screening box includes county outskirts; never delete by city-center radius.
    d['coordinate_review'] = ~(d.latitude.between(33,35) & d.longitude.between(-119,-117))
    d['host_identity_missing'] = d.host_id.isna()
    flags = [c for c in d if c not in raw]
    audit = {'input_rows':len(raw), 'output_rows':len(d), 'source_columns':len(raw.columns),
             'source_sha256':original_hash, 'backup_sha256':sha(backup),
             'exact_duplicate_rows':exact_duplicates, 'repeated_listing_id_rows':repeated_ids,
             'repeated_host_id_rows':int(d.host_id.dropna().duplicated(keep=False).sum()),
             'missing_before':missing_before, 'missing_after':d[raw.columns].isna().sum().astype(int).to_dict(),
             'text_changes':text_changes, 'license_na_markers':license_na_markers,
             'text_examples':[{'id':raw.at[i,'id'],'before':raw.at[i,'name'],'after':d.at[i,'name']}
                              for i in raw.index[raw.name.ne(raw.name.str.strip())][:3]],
             'failed_conversions':failed, 'invalid_values':invalid,
             'identifier_failures':id_failures, 'unknown_group_fills':unknown_groups,
             'price_outlier_threshold':upper, 'license_status_counts':d.license_status.value_counts().to_dict(),
             'flag_counts':{c:int(d[c].sum()) for c in flags if d[c].dtype == bool or str(d[c].dtype)=='boolean'},
             'last_review_min':d.last_review.dropna().min(), 'last_review_max':d.last_review.dropna().max(),
             'types':{c:str(t) for c,t in d.dtypes.items()}}
    metrics = []
    for label, frame in [('All listings',d), ('Minimum stay <=30 nights',d[d.short_stay_eligible]),
                         ('Observed price excluding high flags',d[~d.price_high_outlier])]:
        metrics.append({'population':label,'listings':len(frame),'price_n':int(frame.price.count()),
                        'price_sum':float(frame.price.sum()),'price_mean':float(frame.price.mean()),
                        'price_median':float(frame.price.median()),'availability_n':int(frame.availability_365.count()),
                        'availability_mean':float(frame.availability_365.mean()),
                        'review_rate_n':int(frame.reviews_per_month.count()),
                        'review_rate_mean':float(frame.reviews_per_month.mean()),
                        'reviews_total':int(frame.number_of_reviews.sum())})
    audit['metrics'] = metrics
    original_price = pd.to_numeric(raw.price, errors='coerce')
    audit['reconciliation'] = {'price_sum_before':float(original_price.sum()), 'price_sum_after':float(d.price.sum()),
                               'reviews_before':int(pd.to_numeric(raw.number_of_reviews).sum()),
                               'reviews_after':int(d.number_of_reviews.sum()),
                               'availability_before':int(pd.to_numeric(raw.availability_365).sum()),
                               'availability_after':int(d.availability_365.sum())}
    # Expectations are specified using ORIGINAL values BEFORE cleaned output is examined.
    cases = []
    def case(mask, field, expected, reason):
        idx = raw.index[mask][0]
        value = expected(idx) if callable(expected) else expected
        cases.append({'id':raw.at[idx,'id'], 'field':field,'original':raw.at[idx,field] if field in raw else raw.at[idx,'price'],
                      'expected':value,'reason':reason})
    case(raw.license.eq(''), 'license', None, 'Absent registration is unknown; do not invent a license.')
    case(raw.price.eq(''), 'price', None, 'No observed nightly price; omit only from price denominator.')
    case(raw.number_of_reviews.eq('0') & raw.reviews_per_month.eq(''), 'reviews_per_month', None,
         'Never-reviewed listings have no observed monthly review rate; retain null.')
    case(raw.host_profile_id.str.len().gt(16) & raw.id.ne('2708'), 'host_profile_id', lambda i:raw.at[i,'host_profile_id'],
         'Large identifiers retain every source digit through string loading.')
    case(pd.to_numeric(raw.price,errors='coerce').gt(upper), 'price', lambda i:float(raw.at[i,'price']),
         'High price may be a luxury rental; retain original price and flag it.')
    keyed = d.set_index('id')
    for c in cases:
        actual = keyed.at[c['id'],c['field']]
        actual = None if pd.isna(actual) else actual
        if hasattr(actual,'item'): actual=actual.item()
        c['actual'], c['passed'] = actual, actual == c['expected']
        if c['field']=='price' and actual is not None:
            c['outlier_flag_checked'] = bool(keyed.at[c['id'],'price_high_outlier'])
            c['passed'] &= c['outlier_flag_checked']
    assert all(c['passed'] for c in cases)
    # Select real difficult cases first, then deterministic room/neighborhood coverage (<=50).
    selected = list(dict.fromkeys(c['id'] for c in cases))
    for flag in ['license_missing','price_under_10','minimum_nights_over_365','host_identity_missing','review_counts_inconsistent']:
        selected += d.loc[d[flag],'id'].head(2).tolist()
    selected += d.loc[d.license_status.eq('Exemption claimed'),'id'].head(2).tolist()
    selected += d.groupby(['neighbourhood_group','room_type'],sort=True).head(1).id.tolist()
    selected = list(dict.fromkeys(selected))[:50]
    selected += [i for i in d.id if i not in selected][:50-len(selected)]
    d.to_csv(output/'cleaned_listings.csv',index=False)
    sample = d.set_index('id',drop=False).loc[selected].reset_index(drop=True)
    sample.to_csv(output/'cleaned_sample.csv',index=False)
    raw.set_index('id',drop=False).loc[selected].reset_index(drop=True).to_csv(output/'original_sample.csv',index=False)
    audit['sample_rows']=len(sample)
    pd.DataFrame(cases).to_csv(output/'record_checks.csv',index=False)
    pd.DataFrame(metrics).to_csv(output/'metrics.csv',index=False)
    pd.DataFrame({'column':raw.columns, 'before':[missing_before[c] for c in raw],
                  'after':[audit['missing_after'][c] for c in raw]}).to_csv(output/'missing_counts.csv',index=False)
    d[d.short_stay_price_eligible].groupby(['neighbourhood','room_type'],dropna=False).agg(
        listings=('id','size'),price_n=('price','count'),median_price=('price','median'),
        mean_price=('price','mean'),availability_n=('availability_365','count'),
        mean_available_nights=('availability_365','mean'),review_rate_n=('reviews_per_month','count'),
        mean_reviews_per_month=('reviews_per_month','mean')).reset_index().to_csv(output/'segment_summary.csv',index=False)
    (output/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    (output/'record_checks.json').write_text(json.dumps(cases,indent=2)+'\n')
    assert sha(source)==original_hash and sha(backup)==original_hash
    # Check every source identifier against the CSV after serialization, not just five rows.
    loaded = pd.read_csv(output/'cleaned_listings.csv',dtype='string',keep_default_na=False)
    for c in IDS:
        assert loaded[c].tolist()==d[c].fillna('').tolist(), f'Identifier round-trip changed {c}'
    assert len(loaded)==len(d) and loaded.id.is_unique
    return audit

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=ROOT/'LA_listings.csv')
    p.add_argument('--output',type=Path,default=ROOT/'outputs')
    a=p.parse_args()
    result=clean(a.source,a.output)
    print(json.dumps({'rows':result['output_rows'],'source_sha256':result['source_sha256'],
                      'metrics':result['metrics']},indent=2))
