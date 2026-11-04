"""Independent edge cases and full-source reconciliation for the project contract."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from phase2.clean_data import ROOT, IDS, load_listings, fingerprint, clean_listings
from phase2.backend import (Filters, filter_listings, overview_metrics, market_summary,
    rank_market_segments, geographic_summary, price_distribution, compare_neighbourhoods,
    room_type_overview, dashboard_data)

class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = pd.read_csv(ROOT / 'LA_listings.csv', dtype='string', keep_default_na=False)
        cls.d = load_listings()

    def test_full_source_preserved(self):
        self.assertEqual(len(self.d), 43932)
        for c in IDS:
            self.assertEqual(self.raw[c].str.strip().tolist(), self.d[c].fillna('').tolist())
        for c in ['minimum_nights', 'availability_365', 'number_of_reviews', 'number_of_reviews_ltm']:
            a = pd.to_numeric(self.raw[c], errors='coerce').astype('Float64')
            pd.testing.assert_series_equal(a, self.d[c].astype('Float64'), check_names=False)
        # Exact, correctly rounded comparison (Python float), including coordinates.
        for c in ['price', 'reviews_per_month', 'latitude', 'longitude']:
            source = [float(v) if v.strip() else None for v in self.raw[c]]
            canonical = [None if pd.isna(v) else float(v) for v in self.d[c]]
            self.assertEqual(source, canonical, c)
        self.assertEqual(int(self.d.price.isna().sum()), 5570)
        self.assertEqual(int(self.d.minimum_nights.isna().sum()), 11)
        self.assertEqual(int(self.d.license.isna().sum()), 30740)
        self.assertEqual(int(self.d.reviews_per_month.isna().sum()), 11311)
        self.assertEqual(float(self.d.price.median()), 224)

    def test_cleaner_rejects_conflicting_ids_and_float_ids(self):
        conflicting = pd.concat([self.raw, self.raw.iloc[[0]].assign(price='999')], ignore_index=True)
        with self.assertRaises(ValueError):
            clean_listings(conflicting)
        with self.assertRaises(ValueError):
            clean_listings(self.raw.assign(id=pd.to_numeric(self.raw.id)))

    def test_traveler_trip_and_budget_independently(self):
        f = Filters(budget_usd=250)
        base = filter_listings(self.d, f, apply_budget=False)
        selected = filter_listings(self.d, f)
        expected = self.d.loc[self.d.room_type.eq('Entire home/apt') & self.d.minimum_nights.le(7).fillna(False)]
        self.assertEqual(set(base.id), set(expected.id))
        self.assertEqual(set(selected.id), set(expected.loc[expected.price.le(250).fillna(False)].id))
        metric = overview_metrics(base, 250).iloc[0]
        self.assertEqual(metric.within_budget_n, len(selected))
        self.assertAlmostEqual(metric.within_budget_share, len(selected) / base.price.count())
        self.assertGreater(len(base), len(selected))

    def test_nulls_not_zero_and_empty_contract(self):
        never = self.d.loc[self.d.never_reviewed]
        self.assertTrue(never.reviews_per_month.isna().all())
        row = overview_metrics(self.d.iloc[:0], 250).iloc[0]
        self.assertEqual(row.listing_count, 0)
        self.assertEqual(row.price_n, 0)
        self.assertTrue(pd.isna(row.median_price))
        self.assertTrue(pd.isna(row.within_budget_share))
        self.assertEqual(len(filter_listings(self.d, Filters(room_types=()))), 0)
        self.assertEqual(len(market_summary(self.d.iloc[:0])), 0)

    def test_aggregation_weighting_and_ranking_denominator(self):
        base = filter_listings(self.d)
        summary = market_summary(base, 250)
        self.assertEqual(int(summary.listing_count.sum()), len(base))
        self.assertEqual(int(summary.price_n.sum()), int(base.price.count()))
        # 100 listings with 1 observed price must not qualify for price ranking.
        toy = summary.head(2).copy()
        toy.loc[toy.index[0], ['listing_count', 'price_n', 'median_price']] = [100, 1, 1]
        ranked = rank_market_segments(toy)
        self.assertNotIn(toy.iloc[0].neighbourhood, ranked.neighbourhood.tolist())
        self.assertTrue(rank_market_segments(summary).price_n.ge(30).all())

    def test_geography_and_cdf(self):
        base = filter_listings(self.d)
        geography = geographic_summary(base)
        self.assertEqual(int(geography.listing_count.sum()), len(base))
        self.assertEqual(int(geography.map_n.sum()), int((~base.coordinate_review).sum()))
        curve = price_distribution(base)
        self.assertTrue(curve.nightly_price_usd.is_monotonic_increasing)
        self.assertTrue(curve.cumulative_share.is_monotonic_increasing)
        self.assertAlmostEqual(curve.cumulative_share.iloc[-1], 1)
        self.assertEqual(int(curve.listing_count_at_price.sum()), int(base.price.count()))

    def test_like_for_like_comparison(self):
        compared = compare_neighbourhoods(self.d, Filters(budget_usd=250), ('Hollywood', 'Venice'))
        for area in ['Hollywood', 'Venice']:
            source = self.d.loc[self.d.neighbourhood.eq(area) & self.d.room_type.eq('Entire home/apt') &
                               self.d.minimum_nights.le(7).fillna(False)]
            row = compared.loc[compared.neighbourhood.eq(area)].iloc[0]
            self.assertEqual(row.listing_count, len(source))
            self.assertEqual(row.median_price, source.price.median())
        with self.assertRaises(ValueError):
            compare_neighbourhoods(self.d, Filters(room_types=None), ('Hollywood', 'Venice'))

    def test_room_type_kpis_never_pool(self):
        f = Filters(room_types=None, budget_usd=250)
        views = dashboard_data(self.d, f)
        rooms = views['room_affordability']
        self.assertEqual(int(rooms.listing_count.sum()), int(views['affordability'].listing_count.iloc[0]))
        self.assertEqual(int(rooms.within_budget_n.sum()), int(views['overview'].listing_count.iloc[0]
                         - views['overview'].missing_price_n.iloc[0]))
        entire = rooms.loc[rooms.room_type.eq('Entire home/apt')].iloc[0]
        self.assertEqual((int(entire.within_budget_n), int(entire.price_n)), (3773, 15412))
        self.assertEqual(len(room_type_overview(self.d.iloc[:0])), 0)

    def test_map_tooltip_keeps_population_denominators_separate(self):
        views = dashboard_data(self.d, Filters(budget_usd=250))
        key = ['neighbourhood', 'room_type']
        selected = views['map'].set_index(key)
        pre = views['affordability_segments'].set_index(key)
        chosen = views['segments'].set_index(key)
        self.assertEqual(selected.index.sort_values().tolist(), chosen.index.sort_values().tolist())
        # Selected price_n is the budget-filtered population; the budget
        # denominator comes from pre-budget rows and must never be relabeled.
        self.assertTrue(selected.price_n.eq(chosen.price_n.reindex(selected.index)).all())
        self.assertTrue(selected.pre_budget_price_n.eq(pre.price_n.reindex(selected.index)).all())
        self.assertTrue(selected.within_budget_n.eq(selected.price_n).all())
        self.assertTrue(selected.pre_budget_price_n.ge(selected.price_n).all())
        self.assertTrue(selected.pre_budget_price_n.gt(selected.price_n).any())
        amap = views['affordability_map'].set_index(key)
        self.assertTrue(amap.pre_budget_price_n.eq(pre.price_n.reindex(amap.index)).all())
        self.assertTrue(amap.within_budget_share.dropna().le(1).all())

    def test_reviewed_share_uses_all_selected_rows(self):
        toy = self.d.head(4).copy()
        toy['number_of_reviews'] = pd.array([3, 0, pd.NA, 1], dtype='Int64')
        row = overview_metrics(toy).iloc[0]
        self.assertAlmostEqual(row.reviewed_share, 2 / 4)
        self.assertEqual(row.review_n, 3)
        self.assertTrue(pd.isna(overview_metrics(toy.iloc[:0]).reviewed_share.iloc[0]))

    def test_segment_aggregates_match_listing_formulas(self):
        base = filter_listings(self.d, Filters(room_types=None, trip_nights=None))
        summary = market_summary(base, 250).set_index(['neighbourhood', 'room_type'])
        groups = base.groupby(['neighbourhood', 'room_type'])
        priced = base.dropna(subset=['price']).groupby(['neighbourhood', 'room_type']).price
        expected = pd.DataFrame({
            'listing_count': groups.size(),
            'price_n': groups.price.count(),
            'median_price': priced.median(),
            'price_p25': priced.quantile(.25),
            'within_budget_n': base.assign(w=base.price.le(250).fillna(False)).groupby(
                ['neighbourhood', 'room_type']).w.sum(),
            'median_total_reviews': groups.number_of_reviews.median(),
        }).reindex(summary.index)
        for c in expected:
            pd.testing.assert_series_equal(summary[c].astype('Float64'), expected[c].astype('Float64'),
                                           check_names=False, obj=c)

    def test_bad_controls(self):
        for kwargs in [{'trip_nights': 0}, {'trip_nights': 1.5}, {'budget_usd': -1},
                       {'budget_usd': float('nan')}, {'min_reviews': -1}]:
            with self.assertRaises(ValueError):
                Filters(**kwargs)

    def test_exact_stay_boundary_missing_prices_and_coordinate_screen(self):
        raw = self.raw.head(4).copy().reset_index(drop=True)
        raw['minimum_nights'] = pd.Series(['7', '8', '', '1'], dtype='string')
        raw['price'] = pd.Series(['250', '251', '', ''], dtype='string')
        raw['room_type'] = 'Entire home/apt'
        raw.loc[3, 'latitude'] = '36'
        d, _ = clean_listings(raw)
        selected = filter_listings(d, Filters(budget_usd=250))
        self.assertEqual(selected.id.tolist(), [raw.id.iloc[0]])
        base = filter_listings(d, Filters())
        self.assertEqual(base.id.tolist(), [raw.id.iloc[0], raw.id.iloc[3]])
        self.assertEqual(overview_metrics(base).price_n.iloc[0], 1)
        unknown_price = d.iloc[[2, 3]]
        self.assertTrue(pd.isna(overview_metrics(unknown_price).median_price.iloc[0]))
        self.assertEqual(len(price_distribution(unknown_price)), 0)
        self.assertEqual(int(geographic_summary(base).map_n.sum()), 1)
        self.assertEqual(len(filter_listings(d, Filters(trip_nights=None))), 4)

    def test_fresh_process_rebuild(self):
        manifest = json.loads((ROOT / 'phase2/outputs/manifest.json').read_text())
        with tempfile.TemporaryDirectory(prefix='la_phase2_') as temp:
            subprocess.run([sys.executable, '-m', 'phase2.build', '--output', temp],
                           cwd=ROOT, check=True, capture_output=True)
            for name, expected in manifest['files'].items():
                self.assertEqual(fingerprint(Path(temp) / name), expected, name)
                self.assertEqual(fingerprint(ROOT / 'phase2/outputs' / name), expected, name)

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BackendTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'passed': result.wasSuccessful(), 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'checks': unittest.defaultTestLoader.getTestCaseNames(BackendTests),
              'source_sha256': fingerprint(ROOT / 'LA_listings.csv'),
              'note': 'Automated verification; not a fresh-agent build or team approval.'}
    (ROOT / 'phase2/outputs/verification.json').write_text(json.dumps(report, indent=2) + '\n')
    sys.exit(0 if result.wasSuccessful() else 1)
