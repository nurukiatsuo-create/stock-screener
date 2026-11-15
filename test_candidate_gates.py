"""Selection contracts: missing evidence, explicit exclusions, and S/A boundaries."""
import copy
import unittest
from datetime import datetime
from candidate_gates import apply_selection, position_size, topix_gate
from audit_fundamentals import evidence_key
from market_calendar import expected_price_date


def fixture():
    record = dict(code='1234', published_on='2026-11-13', checked_on='2026-11-13',
        period_end='2027-03-31', prior_period_end='2026-03-31',
        basis='annual_forecast_vs_prior_actual', comparable=True, operating_profit=125,
        prior_operating_profit=100, eps=120, prior_eps=100, source_url='https://example.com/ir.pdf')
    inputs = {'shikiho': {'rows': [dict(code='1234', name='テスト', source_verified=True,
                    source_edition='2026秋', source_locator='原本p123', source_claim='増益', verified_on='2026-11-13')]},
              'fundamentals': {'records': [record]}, 'checks': {'records': []},
              'topix': dict(verified=True, complete=True, source_url='https://www.jpx.co.jp/test-list.pdf',
                    published_on='2026-11-01', checked_on='2026-11-13', valid_until='2026-11-30',
                    transition_codes=[], new_inclusions=[])}
    row = dict(code='1234', name='テスト', candidate=True, entry_group='initial_break',
               status='初動の技術条件該当', close=1000, avg_turnover_5d_yen=50000000,
               box={'valid': True, 'date': '2026-11-13'})
    strategy = dict(version=3, observations=[row], candidates=[row], available_yen=500000, holdings=[])
    return strategy, inputs, {'selection_policy': {'risk_per_trade_yen': 10000}}


def run(strategy, inputs, config, as_of='2026-11-13', price_date='2026-11-13'):
    return apply_selection(strategy, inputs, config, as_of, price_date)[0]


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.s, self.i, self.c = fixture()

    def test_all_gates_are_required_and_a_is_default(self):
        r = run(self.s, self.i, self.c)
        self.assertEqual(r['candidates'][0]['rank'], 'A')
        self.assertEqual(r['candidates'][0]['order_preview']['shares'], 100)
        self.assertNotIn('selection_version', self.s)
        for key in ('shikiho', 'fundamentals'):
            inputs = copy.deepcopy(self.i)
            inputs[key]['rows' if key == 'shikiho' else 'records'] = []
            if key == 'shikiho': inputs['fundamentals']['records'] = []
            result = run(self.s, inputs, self.c)
            self.assertEqual(result['candidates'], [])
            self.assertTrue(result['observations'][0]['technical_candidate'])
            self.assertEqual(result['observations'][0]['selection_status'], 'pending')

    def test_blank_topix_never_means_nonmember(self):
        for snapshot in ({}, {'verified': False, 'transition_codes': []}):
            self.i['topix'] = snapshot
            self.assertEqual(run(self.s, self.i, self.c)['candidates'], [])

    def test_transition_exclusion_wins_over_missing_fundamentals(self):
        self.i['topix']['transition_codes'] = ['1234']
        self.i['fundamentals']['records'] = []
        r = run(self.s, self.i, self.c)
        self.assertEqual(r['observations'][0]['selection_status'], 'excluded')
        self.assertIn('TOPIX', r['excluded'][0]['status'])

    def test_s_requires_full_pass_and_has_event_boundary(self):
        self.i['topix']['new_inclusions'] = [{'code': '1234', 'effective_on': '2026-11-13'}]
        self.assertEqual(run(self.s, self.i, self.c)['candidates'][0]['rank'], 'S')
        self.i['topix']['new_inclusions'][0]['effective_on'] = '2026-11-12'
        self.assertEqual(run(self.s, self.i, self.c)['candidates'][0]['rank'], 'A')
        self.i['shikiho']['rows'][0]['source_verified'] = False
        self.assertEqual(run(self.s, self.i, self.c)['candidates'], [])

    def test_topix_invalid_dates_hosts_and_conflicts_fail_closed(self):
        for key, value in [('valid_until', '2026-11-12'), ('checked_on', '2026-11-14'),
                           ('source_url', 'https://jpx.co.jp.example.com/list'), ('complete', False)]:
            snapshot = copy.deepcopy(self.i['topix']); snapshot[key] = value
            self.assertEqual(topix_gate('1234', snapshot, '2026-11-13')['status'], 'unknown')
        self.i['topix']['transition_codes'] = ['1234']
        self.i['topix']['new_inclusions'] = [{'code': '1234', 'effective_on': '2026-11-13'}]
        self.assertEqual(topix_gate('1234', self.i['topix'], '2026-11-13')['status'], 'unknown')

    def test_liquidity_is_an_actual_gate(self):
        self.s['observations'][0]['avg_turnover_5d_yen'] = 1000000
        self.assertEqual(run(self.s, self.i, self.c)['observations'][0]['selection_status'], 'excluded')
        self.s['observations'][0]['avg_turnover_5d_yen'] = None
        self.assertEqual(run(self.s, self.i, self.c)['observations'][0]['selection_status'], 'pending')

    def test_valid_watch_is_not_initial_candidate(self):
        self.s['observations'][0].update(candidate=False, entry_group='pre_break', status='突破直前')
        r = run(self.s, self.i, self.c)
        self.assertEqual(r['observations'][0]['selection_status'], 'watch')
        self.assertEqual(r['candidates'], [])

    def test_reapplying_selection_keeps_original_technical_signal(self):
        original = copy.deepcopy(self.i)
        self.i['topix'] = {}
        pending = run(self.s, self.i, self.c)
        restored = run(pending, original, self.c)
        self.assertEqual(len(restored['candidates']), 1)
        self.assertEqual(restored['observations'][0]['technical_status'], '初動の技術条件該当')

    def test_whole_batch_stale_is_not_considered_current(self):
        self.s['observations'][0]['box']['date'] = '2026-11-12'
        r = run(self.s, self.i, self.c, price_date='2026-11-12')
        self.assertEqual(r['observations'][0]['gates']['price_data']['status'], 'unknown')
        self.assertEqual(r['candidates'], [])

    def test_counts_partition_and_unprocessed_source_are_visible(self):
        self.i['shikiho']['rows'].append(dict(code='5678', name='未計算'))
        r = run(self.s, self.i, self.c)
        counts = r['selection_counts']
        self.assertEqual(sum(counts['final'].values()), counts['observations'])
        self.assertEqual(counts['not_calculated_codes'], ['5678'])

    def test_additions_cannot_bypass_audit_gates(self):
        self.s['holdings'] = [{'code': '1234', 'add_candidate': True}]
        self.i['topix'] = {}
        self.assertFalse(run(self.s, self.i, self.c)['holdings'][0]['add_candidate'])

    def test_risk_size_cash_and_liquidity_caps(self):
        self.assertIsNone(position_size(1000, 1000000, None, 50000000)['shares'])
        self.assertEqual(position_size(1000, 1000000, 10000, 50000000)['shares'], 100)
        self.assertEqual(position_size(1000, 90000, 10000, 50000000)['shares'], 0)
        self.assertEqual(position_size(1000, 1000000, 10000, 100000)['shares'], 0)
        with self.assertRaises(ValueError): position_size(1000, 1000000, 0, 50000000)

    def test_calendar_weekend_holiday_and_release_buffer(self):
        for stamp, expected in [('2026-11-15T17:00:00+09:00', '2026-11-13'),
                                ('2026-11-03T17:00:00+09:00', '2026-11-02'),
                                ('2026-11-16T15:59:00+09:00', '2026-11-13'),
                                ('2026-11-16T16:00:00+09:00', '2026-11-16')]:
            self.assertEqual(expected_price_date(datetime.fromisoformat(stamp)), expected)


if __name__ == '__main__':
    unittest.main()
