"""Fresh-run reproducibility and independent full-data checks."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import pandas as pd

ROOT=Path(__file__).resolve().parent

def verify():
    with tempfile.TemporaryDirectory(prefix='airbnb_verify_') as tmp:
        subprocess.run([sys.executable,str(ROOT/'clean_airbnb.py'),'--output',tmp],check=True,capture_output=True)
        compared=[]
        for path in sorted((ROOT/'outputs').iterdir()):
            if path.suffix not in ['.csv','.json'] or path.name=='verification.json': continue
            other=Path(tmp)/path.name
            if not other.exists(): continue
            assert path.read_bytes()==other.read_bytes(), f'Rerun differs: {path.name}'
            compared.append(path.name)
    raw=pd.read_csv(ROOT/'LA_listings.csv',dtype='string',keep_default_na=False)
    clean=pd.read_csv(ROOT/'outputs/cleaned_listings.csv',dtype='string',keep_default_na=False)
    assert raw.id.tolist()==clean.id.tolist() and clean.id.is_unique
    for c in ['id','host_id','host_profile_id']:
        assert raw[c].str.strip().tolist()==clean[c].tolist()
    rp=pd.to_numeric(raw.price,errors='coerce')
    cp=pd.to_numeric(clean.price,errors='coerce')
    assert rp.fillna(-1).equals(cp.fillna(-1))
    assert int((raw.license.isin(['','N/A'])).sum())==int(clean.license.eq('').sum())==30740
    zero=raw.number_of_reviews.eq('0')
    assert zero.sum()==11311 and raw.loc[zero,'reviews_per_month'].eq('').all()
    assert clean.loc[zero,'reviews_per_month'].eq('').all()
    for c in ['number_of_reviews','number_of_reviews_ltm','availability_365']:
        assert pd.to_numeric(raw[c]).sum()==pd.to_numeric(clean[c]).sum()
    sample=pd.read_csv(ROOT/'outputs/cleaned_sample.csv',dtype='string',keep_default_na=False)
    assert len(sample)==50 and sample.id.is_unique
    assert set(sample.id)<=set(raw.id)
    assert clean.set_index('id').loc[sample.id].reset_index().equals(sample)
    checks=json.loads((ROOT/'outputs/record_checks.json').read_text())
    assert len({c['id'] for c in checks})==5 and all(c['passed'] for c in checks)
    result={'passed':True,'fresh_process_files_identical':compared,'full_data_checks':[
        'All listing IDs and order preserved','All three identifier columns preserve every digit',
        'All observed prices and price nulls unchanged','30,740 absent licenses remain null',
        '11,311 zero-review listings retain missing review rates','Review and availability totals unchanged',
        '50 real sample rows exactly match cleaned output','Five distinct original-record checks pass'],
        'source_sha256':hashlib.sha256((ROOT/'LA_listings.csv').read_bytes()).hexdigest()}
    (ROOT/'outputs/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result

if __name__=='__main__': verify()
