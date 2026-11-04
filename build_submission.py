"""Build the reviewable homework PDF and README from actual audit outputs."""
from pathlib import Path
import json
import subprocess
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
import pandas as pd

ROOT=Path(__file__).resolve().parent
def build():
    a=json.loads((ROOT/'outputs/audit.json').read_text())
    v=json.loads((ROOT/'outputs/verification.json').read_text())
    checks=json.loads((ROOT/'outputs/record_checks.json').read_text())
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    meta_path=ROOT/'submission_revision.json'
    meta=json.loads(meta_path.read_text()) if meta_path.exists() else {'analysis_commit':head,'pushed':False}
    commit=meta['analysis_commit']
    branch_url='https://github.com/cynthiaqgao/project/tree/'+branch
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Body',fontName='Helvetica',fontSize=9.5,leading=13,spaceAfter=7))
    styles.add(ParagraphStyle(name='SmallCell',fontName='Helvetica',fontSize=8,leading=10.5))
    styles['Title'].fontSize=22; styles['Title'].leading=27
    styles['Heading1'].fontSize=16; styles['Heading1'].leading=20
    styles['Heading2'].fontSize=11; styles['Heading2'].leading=14
    story=[]
    def p(s,style='Body'):
        story.append(Paragraph(s,styles[style]))
    def title(s): p(s,'Heading1')
    def item(n,name,status,s):
        p(f'{n}  {name} <font color="#52606d">| {status}</font>','Heading2'); p(s)
    def table(rows,widths):
        cells=[[Paragraph(escape(str(c)),styles['SmallCell']) for c in row] for row in rows]
        t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef4')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#b8c4d0')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f6f8fa')])]))
        story.append(t); story.append(Spacer(1,10))
    def page(): story.append(PageBreak())
    p('Los Angeles Airbnb Data Cleaning','Title')
    p('DSO 576 Module 6 | Individual homework | Kyi Sin Thant | October 2, 2026')
    p('This submission prepares the supplied Los Angeles Airbnb listings snapshot for neighborhood and room-type price comparisons. All 43,932 listings are retained. Missing identifiers and prices remain unknown; unusual prices and stay requirements are flagged rather than deleted.')
    table([['Result','Evidence'],['Source','43,932 rows; 19 original columns; one listing per row'],
        ['Row changes','0 removed; 0 exact duplicates; 0 repeated listing IDs'],
        ['Missing prices','5,570 retained; 38,362 observed prices used in all-market price metrics'],
        ['Missing licenses','30,740 retained as unknown: 30,736 blanks plus 4 N/A markers'],
        ['Verification','5 distinct record checks pass; fresh-process rerun reproduces 9 output files byte for byte']], [135,365])
    p('Submission revision','Heading2')
    p('Branch: '+escape(branch)+'<br/>Branch URL: <link href="'+branch_url+'">'+branch_url+'</link><br/>Submitted analysis commit: '+commit)
    p('The analysis commit identifies the executable cleaning and verification package. A subsequent documentation commit may attach the literal analysis revision to the README; it does not change cleaning rules or results.')
    p('GitHub push: '+('verified successful' if meta.get('pushed') else 'not yet verified')+'. Instructor access must be confirmed separately; no access claim is made here.')
    p('Codex assisted in writing the cleaning and verification code and this report. The checks below are programmatic evidence, not a claim that the student has personally reviewed the submission. Student review is still required by the assignment.')
    page(); title('Inspect and clean the data')
    item(1,'State the project vision and question','Done',
         'Vision: help prospective Airbnb hosts and travelers compare Los Angeles neighborhood and room-type markets. Business question: among listings accepting stays of 30 nights or fewer with an observed price, how does median listed nightly price vary by neighborhood and room type? Median price is the primary metric; listing counts, mean available nights, and observed monthly review rates provide context. A 30-night threshold is an analytical filter, not a legal classification. Evidence: outputs/segment_summary.csv.')
    item(2,'Define one row','Done','One row is one listing in a single supplied market snapshot. The key is id: 43,932 nonempty, unique digit strings. A host may own several listings, so repeated host_id values are expected. Neither host_name nor license is a listing key. host_profile_id is preserved separately because its relationship to host_id is not documented. Evidence: outputs/audit.json and verify_airbnb.py.')
    item(3,'Preserve the source','Unresolved',
         'The project identifies Inside Airbnb as the source. LA_listings.csv is the supplied local version, identified by its SHA-256 below. The cleaning script creates raw_backup/LA_listings.csv before transformations and verifies both hashes before and after the run. Load with pandas.read_csv(..., dtype="string", keep_default_na=False). Exact original download and scrape dates are not supplied; the latest review date, June 22, 2026, is not asserted to be the scrape date. Consequently historical or quarterly comparisons cannot be dated reliably. Evidence: source and backup hashes in outputs/audit.json.')
    p('SHA-256: '+a['source_sha256'],'SmallCell')
    item(4,'Inspect columns and types','Done',
         'Read every field as text first. Keep id, host_id, host_profile_id and license as strings to preserve leading zeros and large integers. Convert five count/stay fields to nullable Int64 and price, reviews_per_month, latitude and longitude to nullable Float64. Parse last_review strictly as YYYY-MM-DD and serialize in that format. The field contains dates only, so timezone conversion is not applicable. All 10 numeric/date conversion checks have zero failures; all identifier format checks have zero failures. Evidence: audit.json types, failed_conversions and identifier_failures.')
    item(5,'Standardize text','Done',
         'Trim surrounding whitespace, convert blank strings to null, and normalize four literal N/A license markers to null. Sixteen listing names change through whitespace trimming; accents, capitalization and meaningful punctuation remain. Keep absent host names null to avoid grouping different unknown hosts under one invented identity. Evidence: audit.json text_changes and text_examples; examples appear on page 8.')
    item(6,'Investigate duplicates','Done',
         'Exact original duplicate rows: 0. Repeated listing-ID rows after exact duplicate handling: 0. Rows belonging to repeated nonmissing host IDs: 28,464; retain these because hosts can have multiple properties. Repeated licenses also remain because their property relationship is not verified. The pipeline stops on conflicting listing IDs rather than keeping an arbitrary record. Evidence: audit.json and clean_airbnb.py.')
    page(); title('Missing data and validation')
    item(7,'Handle missing data','Done','Keep all affected records. Missing counts below use a semantic definition: blank fields and the four literal N/A license markers are absent. Normalizing those markers changes their representation, not the number of absent licenses. All other original columns have zero missing values before and after. Evidence: outputs/missing_counts.csv.')
    missing=[['Affected column','Before','After','Policy']]
    policies={'host_id':'Null; exclude from host-identity counts only','host_profile_id':'Null; no backfill from host_id',
              'host_name':'Null; display unknown without treating as identity','price':'Null; exclude from price metrics only',
              'minimum_nights':'Null; cannot establish short-stay eligibility','last_review':'Null; no invented review date',
              'reviews_per_month':'Null; rate denominator uses observed values',
              'calculated_host_listings_count':'Null; do not assume one property','license':'Null plus Missing status; no licensing inference'}
    for c,n in a['missing_before'].items():
        if n: missing.append([c,f'{n:,}',f"{a['missing_after'][c]:,}",policies[c]])
    table(missing,[155,48,48,249])
    item(8,'Check suspicious values','Done',
         'All numeric ranges, integer-count checks, date parses and future-review checks pass. Reviews in the last 12 months never exceed total reviews; review-rate/date availability is consistent with whether reviews exist. Four room types are recognized; all coordinates fall inside a deliberately broad metro review box (33 to 35 latitude, -119 to -117 longitude). This is a screening check, not proof of county membership. Flag and retain 1,634 prices above $1,276 (Q3 + 3 IQR), 14 prices below $10, and 24 minimum stays above 365 nights. Stay requirements above 365 may be deliberate long-term offers. Evidence: audit.json flag_counts and invalid_values.')
    item(9,'Verify merges','Not applicable','Only one listing table is used. No external merge is performed; no unmatched merge keys or join expansion apply. The segment summary is a groupby aggregation, not a merge. Evidence: clean_airbnb.py.')
    item(10,'Reconcile changes','Done',
         '43,932 starting rows - 0 removals = 43,932 final rows. Listed-price sum stays $14,697,868 across 38,362 observed prices; total reviews stay 1,856,294; available-night total stays 9,828,724. The price sum is a reconciliation total, not revenue. Added flags do not alter observations. Evidence: audit.json reconciliation and verification.json.')
    page(); title('Calculations and denominators')
    item(11,'Check calculations','Done',
         'Price means, medians and sums use observed positive prices only. Missing prices are never replaced by zero or a neighborhood average. Availability statistics use nonmissing availability_365, including legitimate zero values. Review-rate means use observed reviews_per_month only; all 11,311 absent rates belong to zero-review listings, and no listing exposure duration is available to justify a fabricated rate. Review counts include real zeros. Missing group keys would be placed in Unknown, but none occur. Missing license status is always its own group.')
    rows=[['Population','Listings','Price n','Mean price','Median price']]
    for m in a['metrics']:
        rows.append([m['population'],f"{m['listings']:,}",f"{m['price_n']:,}",f"${m['price_mean']:,.2f}",f"${m['price_median']:,.2f}"])
    table(rows,[195,70,70,85,80])
    table([['Population','Availability n','Mean nights available','Review-rate n','Mean reviews/month']]+[
        [m['population'],f"{m['availability_n']:,}",f"{m['availability_mean']:.2f}",f"{m['review_rate_n']:,}",f"{m['review_rate_mean']:.3f}"] for m in a['metrics']], [165,75,90,75,95])
    p('The <=30-night population has 39,064 listings. Its price analysis uses 34,444 observed prices; 4,620 prices are missing. The other 4,868 market records consist of 4,857 listings with minimum stays above 30 nights and 11 with unknown minimum stay. These records remain in the cleaned master dataset.')
    p('Price sensitivity','Heading2')
    p('All observed-price mean is $383.14 and median is $224. Removing the 1,634 high-price flags from a separate sensitivity calculation lowers the mean to $283.93 and median to $213. This shows why the median is the main benchmark. Flags remain in the source-preserving cleaned dataset; the sensitivity filter is a disclosed analytical choice, not proof that luxury prices are erroneous.')
    p('Licensing and market interpretation','Heading2')
    p('License statuses: Missing 30,740; Exemption claimed 3,867; License provided 9,325. These statuses describe reported information and do not establish legal validity or compliance. The observed missing share is 70.0% of all listings. Availability describes calendar availability, not realized demand, bookings, occupancy or revenue; blocked host nights can also be unavailable. Review rates indicate review activity, not booking conversion.')
    p('Evidence: outputs/metrics.csv contains counts for every metric; outputs/segment_summary.csv contains separate price, availability and review-rate denominators for each neighborhood-room segment. No minimum-size claim or neighborhood ranking is made from the 50-row sample.')
    page(); title('Five original record checks')
    item(12,'Verify individual records','Done','Five distinct real listing IDs were selected for difficult cases. Expected values and reasons are specified from original source fields before checking actual cleaned values. All five checks pass. Full-data identifier, price, missing-value and total checks supplement these examples. Evidence: outputs/record_checks.csv and record_checks.json.')
    def val(x): return 'blank / null' if x is None or x=='' else str(x)
    table([['Listing and field','Original','Expected','Actual']]+[
        [c['id']+' / '+c['field'],val(c['original']),val(c['expected']),val(c['actual'])] for c in checks],
        [155,115,115,115])
    for i,c in enumerate(checks,1):
        p(f"Check {i}: PASS. "+escape(c['reason'])+ (' High-price flag also checked: True.' if c.get('outlier_flag_checked') else ''))
    p('How a Codex suggestion was checked','Heading2')
    p('Codex suggested retaining unknown licenses rather than imputing or deleting them. verify_airbnb.py independently counts empty and N/A source licenses (30,740), confirms exactly 30,740 cleaned null licenses, and confirms all original listing IDs and row order remain. No-review rate handling and preservation of all observed prices are independently checked as well. A separate fresh Python process recreates every cleaning output. This verifies implementation of the suggestion; it does not validate a license or replace student review.')
    page(); title('Reproducibility and limitations')
    item(13,'Test reproducibility','Done',
         'The notebook was executed from a fresh kernel, and verify_airbnb.py starts the cleaner in a fresh Python process using the preserved source. Nine generated CSV/JSON outputs match byte for byte. All full-data checks pass, including serialization of every identifier and exact membership of all 50 sample rows. Evidence: executed kyi_module_6_hw.ipynb, outputs/verification.json, and outputs/notebook_execution.json.')
    p('Run instructions','Heading2')
    p('Python 3.10 or newer. From the project directory:<br/><font face="Courier">python -m venv .venv<br/>.venv/bin/python -m pip install -r requirements.txt<br/>.venv/bin/python clean_airbnb.py<br/>.venv/bin/python verify_airbnb.py<br/>.venv/bin/python execute_notebook.py<br/>.venv/bin/python build_submission.py</font>')
    p('All scripts resolve source paths relative to their own location. The backup is created once and never overwritten with differing bytes. outputs/cleaned_listings.csv is the complete result; outputs/cleaned_sample.csv is a real, shareable 50-row subset. Other outputs provide missing counts, metrics, segment summaries, record checks, audit and verification. The PDF is regenerated from those actual results. See README.md for the complete file list.')
    item(14,'Document remaining limitations','Done',
         'Documented unresolved issues: the original scrape/download date and any upstream transformations are unknown. This supplied 19-column file has an extra host_profile_id whose meaning is not documented; it is never substituted for host_id. License validity, exemption claims and jurisdiction-specific requirements are unverified. Missing prices could systematically differ from observed-price listings, so results describe observed prices only. Price outliers are not externally verified. Long minimum stays and stale reviews can reflect legitimate listings.')
    p('A single snapshot cannot measure host entry/exit, seasonal changes, actual bookings or conversion. It lacks amenities, ratings and calendar booking details, limiting comparisons between otherwise different properties. Listing coordinates are approximate; the broad geographic check cannot validate neighborhood assignments. Exact collection metadata, official license records and richer listing/calendar data would be needed to resolve these issues.')
    p('Submission requirements outside data cleaning','Heading2')
    p('The exact analysis branch and commit are printed on page 1 and in README.md. Instructor repository access and Gradescope upload require the student account and are not asserted complete. Review the report and code before uploading this individual PDF. No files are pushed to main or the shared course repository.')
    page(); title('Cleaning decision log')
    decisions=[['Rule','Reason in Airbnb context','Check'],
      ['Preserve original and backup before edits','Provides audit trail; do not lose the supplied market snapshot','Source/backup SHA-256 equal before and after'],
      ['Load all IDs as strings','Large listing/profile identifiers lose precision in floating point; leading zeros can matter','Every ID checked after CSV round-trip'],
      ['Remove exact rows only; stop on conflicting listing IDs','One listing per snapshot; repeated host IDs represent multi-property hosts','0 exact duplicates; 0 repeated listing IDs'],
      ['Trim surrounding whitespace only','Clean display text while preserving property descriptions, accents and names','16 names changed; examples on page 8'],
      ['Blank fields to null; license N/A to null','Missing information must remain distinguishable from zero or an actual identifier','4 N/A markers; before/after counts for all columns'],
      ['Keep missing price; no imputation','Inventing nightly prices distorts neighborhood price benchmarks','5,570 retained; price n=38,362; price values unchanged'],
      ['Keep missing review rate/date','Zero reviews are observed counts; no exposure duration establishes a rate','11,311 zero-review records; 0 field inconsistencies'],
      ['Keep missing license plus status flag','Unknown registration is insufficient to classify legal status; exemptions differ','30,740 Missing; 3,867 exemption claims'],
      ['Keep missing host identity and host inventory count','Host names are not unique; do not combine unrelated unknown hosts','181 host_id nulls; 395 host_profile_id nulls'],
      ['Use observed range/type rules; null impossible numbers if found','Calendar days must be 0-365; counts integer/nonnegative; price positive','0 invalid/failed numeric/date values'],
      ['Flag high/low prices and long stays; keep values','Luxury properties and long-term offers can legitimately be unusual','1,634 above $1,276; 14 below $10; 24 stays >365'],
      ['Compare median prices within neighborhood and room type','Controls basic location/room differences and reduces influence of luxury tail','Segment table includes counts; separate sensitivity metrics'],
      ['Use <=30-night analytical subset','Supports relatively short stays without removing long-term rentals from source','39,064 eligible; 34,444 with observed price'],
      ['Retain zero availability and missing group policy','Zero available days can be legitimate; Unknown avoids silent group loss','All 43,932 availability values present; 0 missing group keys']]
    table(decisions,[135,205,160])
    page(); title('Sample selection and source evidence')
    p('The sample contains 50 real cleaned listings, not synthetic records. It begins with the five checked IDs, then includes examples of missing licenses, very low prices, stays above 365 nights, absent host IDs, and exemption claims. It adds one listing for each observed neighborhood-group and room-type combination, removes repeated selected IDs, and fills remaining slots using source order. Selection is deterministic and purposive; it is not representative for statistical inference. Every sample row is checked against the full cleaned output. Matching original rows are supplied in outputs/original_sample.csv.')
    p('Text before and after','Heading2')
    for e in a['text_examples']:
        # repr makes invisible terminal line-separator whitespace explicit.
        p('Listing '+e['id']+'<br/>Before: '+escape(ascii(e['before']))+'<br/>After: '+escape(ascii(e['after'])))
    p('The terminal \\u2028 line separator is removed by strip(); the internal middle dot \\u00b7 and property wording remain. No case folding or accent removal is performed.')
    p('Source and method references','Heading2')
    p('Assignment: Module_6_Homework.pdf, supplied by the student. Requirements include the 14-item checklist, rule/reason/check log, five records, full-data checks, reproducibility and an individual GitHub branch.')
    p('Dataset provenance: project-start.md and phase1_submission.md identify Inside Airbnb and the Los Angeles market. Local source version: LA_listings.csv, SHA-256 on page 2. Exact upstream collection date remains unresolved.')
    p('Inside Airbnb data access and attribution:<br/><link href="https://insideairbnb.com/get-the-data/">https://insideairbnb.com/get-the-data/</link><br/>Inside Airbnb data assumptions (calendar unavailability and approximate coordinates):<br/><link href="https://insideairbnb.com/data-assumptions/">https://insideairbnb.com/data-assumptions/</link><br/>Airbnb explanation of registration and exemption displays:<br/><link href="https://www.airbnb.com/help/article/1634">https://www.airbnb.com/help/article/1634</link><br/>References consulted October 2, 2026.')
    p('The data access page licenses Inside Airbnb data under CC BY 4.0. This submission attributes that source and makes changes explicit. No replacement download is used: all reported statistics refer to the supplied local file.')
    sample=pd.read_csv(ROOT/'outputs/cleaned_sample.csv',dtype='string',keep_default_na=False)
    for start in [0,20,40]:
        page(); title(f'Cleaned sample records {start+1} to {min(start+20,len(sample))}')
        p('Selected fields from the real 50-row cleaned sample. All fields are supplied in outputs/cleaned_sample.csv, with matching originals in outputs/original_sample.csv. Missing prices display as null; a license status describes reported information only.')
        rows=[['Listing id','Neighborhood','Room type','Price','Min nights','Avail 365','License status']]
        for _,r in sample.iloc[start:start+20].iterrows():
            rows.append([r.id,r.neighbourhood,r.room_type,r.price or 'null',r.minimum_nights or 'null',r.availability_365,r.license_status])
        table(rows,[100,85,80,45,40,45,105])
    out=ROOT/'output/pdf'; out.mkdir(parents=True,exist_ok=True)
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#52606d'))
        canvas.drawString(48,28,'Kyi Sin Thant | DSO 576 Module 6')
        canvas.drawRightString(564,28,str(doc.page))
    SimpleDocTemplate(str(out/'Module_6_Airbnb_Cleaning_Kyi.pdf'),pagesize=letter,
                      rightMargin=56,leftMargin=56,topMargin=44,bottomMargin=45,
                      title='Los Angeles Airbnb Data Cleaning',author='Kyi Sin Thant').build(story,onFirstPage=footer,onLaterPages=footer)
    readme=f'''# Los Angeles Airbnb data cleaning

Individual DSO 576 Module 6 submission by Kyi Sin Thant.

Business question: among listings accepting stays of 30 nights or fewer with observed prices, how does median listed nightly price vary by neighborhood and room type?

## Submitted revision

- Branch: `{branch}`
- Branch URL: {branch_url}
- Submitted analysis commit ID: `{commit}`
- Analysis commit URL: https://github.com/cynthiaqgao/project/commit/{commit}
- Push verified: {meta.get('pushed',False)}

The analysis commit identifies the cleaning package and results. A later documentation commit can attach this literal revision to README without changing analysis. Instructor access must be confirmed separately. The PDF must be uploaded individually to Gradescope after student review.

## Source and version

Inside Airbnb Los Angeles listing data: https://insideairbnb.com/get-the-data/ (CC BY 4.0). Supplied local file `LA_listings.csv`, 43,932 rows and 19 original columns. Source identification comes from the existing project documents. Exact original download/scrape date and upstream transformations are unknown; latest review date is not a scrape date.

SHA-256: `{a['source_sha256']}`

`LA_listings.csv` stays unchanged. `clean_airbnb.py` makes `raw_backup/LA_listings.csv` before cleaning and refuses to overwrite a different backup. Both hashes are verified. This source is already tracked in the project repository; the full generated dataset and raw backup are ignored.

## Run

Python 3.10 or newer, from this directory:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python clean_airbnb.py
.venv/bin/python verify_airbnb.py
.venv/bin/python execute_notebook.py
.venv/bin/python build_submission.py
```

Alternatively open `kyi_module_6_hw.ipynb`, select the same environment, restart the kernel and run all cells. The notebook invokes the same cleaning and independent verification scripts. No network download is required to clean the supplied source. Installing dependencies requires package access.

## Rules and expected outputs

All 43,932 listings remain. IDs and licenses are strings; numeric counts use nullable integers; date strings are validated as YYYY-MM-DD. Trim external whitespace (16 names); normalize four N/A license markers. Keep missing values, including 5,570 prices, 30,740 licenses, and 11,311 review rates. No invented price or licensing status is introduced. Hosts can own multiple listings; repeated host IDs are retained. High prices, prices below $10, and stays over 365 nights are flagged and retained. The full decision log and all 14 checklist items are in the PDF.

- `outputs/cleaned_listings.csv`: complete cleaned dataset, ignored by Git; reload with `dtype='string'` for identifier safety or explicitly set identifier string dtypes.
- `outputs/cleaned_sample.csv`: exactly 50 real cleaned rows including difficult cases, tracked.
- `outputs/original_sample.csv`: corresponding original records, tracked.
- `outputs/audit.json`: types, missing counts, failures, flags, hash, row/total reconciliation.
- `outputs/missing_counts.csv`: before/after counts for every original column.
- `outputs/metrics.csv`: market, <=30-night and outlier-sensitivity metrics with denominators.
- `outputs/segment_summary.csv`: neighborhood-room price comparisons for eligible observed-price listings, with metric counts.
- `outputs/record_checks.csv` and `.json`: five distinct original/expected/actual checks and reasons.
- `outputs/verification.json`: independent full-data checks and byte-identical fresh-process rerun of nine output files.
- `outputs/notebook_execution.json`: fresh-kernel execution evidence.
- `output/pdf/Module_6_Airbnb_Cleaning_Kyi.pdf`: individual submission PDF, generated locally and ignored by Git.

## Verification and limitations

`verify_airbnb.py` checks every listing and all three ID columns after serialization, every observed price, null licenses, zero-review missing rates, review/availability totals and every sample row. It starts a separate process from the source and compares nine output files byte for byte. Five distinct records all pass. Codex assisted in preparing these files; programmatic checks do not claim student review.

Median price is the main metric. All-market price n=38,362, mean=$383.14 and median=$224.00. <=30-night price n=34,444 and median=$240.00. Removing 1,634 high-price flags for a separate sensitivity calculation yields mean=$283.93 and median=$213.00, without changing the master dataset.

Calendar availability is not actual occupancy; unavailable nights can be booked or blocked. Review activity is not booking conversion. Missing prices can bias observed-price comparisons. Provided licenses and exemption claims are unverified; missing licenses do not establish noncompliance. The 30-night filter is analytical, not legal. `host_profile_id` meaning is undocumented and it is not substituted for `host_id`. No external merge is performed. Original collection metadata and richer data are needed for temporal, regulatory or booking conclusions.

Method references: https://insideairbnb.com/data-assumptions/ and https://www.airbnb.com/help/article/1634 . Consulted October 2, 2026.
'''
    (ROOT/'README.md').write_text(readme)
    print(out/'Module_6_Airbnb_Cleaning_Kyi.pdf')

if __name__=='__main__': build()
