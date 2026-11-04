"""Rebuild canonical data and dashboard tables with source and output hashes."""
import argparse
import json
from pathlib import Path
import pandas as pd
from phase2.clean_data import ROOT, clean_listings, fingerprint
from phase2.backend import Filters, dashboard_data, compare_neighbourhoods

def build(output=ROOT / 'phase2/outputs'):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'LA_listings.csv'
    before = fingerprint(source)
    raw = pd.read_csv(source, dtype='string', keep_default_na=False)
    d, audit = clean_listings(raw)
    d.to_csv(output / 'listings.csv', index=False)
    pd.DataFrame({'column': raw.columns,
                  'raw_blank_n': [int(raw[c].str.strip().eq('').sum()) for c in raw],
                  'clean_missing_n': [int(d[c].isna().sum()) for c in raw]}).to_csv(output / 'missingness.csv', index=False)
    # Default UI, plus an explicit illustrative $250/night affordability scenario.
    for scenario, filters in [('default', Filters()), ('budget250', Filters(budget_usd=250))]:
        bundle = dashboard_data(d, filters)
        for name, table in bundle.items():
            if name != 'listings':
                table.to_csv(output / f'{scenario}_{name}.csv', index=False)
    compare_neighbourhoods(d, Filters(budget_usd=250), ('Hollywood', 'Venice')).to_csv(
        output / 'example_comparison.csv', index=False)
    audit['source_sha256'] = before
    audit['source_path'] = 'LA_listings.csv'
    audit['snapshot_date'] = None
    audit['source_unchanged'] = fingerprint(source) == before
    assert audit['source_unchanged']
    (output / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    manifest = {'contract_version': '1.0', 'source_sha256': before,
                'files': {p.name: fingerprint(p) for p in sorted(output.iterdir())
                          if p.suffix in ['.csv', '.json'] and p.name not in ['manifest.json', 'verification.json']}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return audit

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'phase2/outputs')
    args = parser.parse_args()
    audit = build(args.output)
    print(json.dumps({k: audit[k] for k in ['input_rows', 'output_rows', 'source_sha256', 'flags']}, indent=2))
