import unittest
import json
import pandas as pd
from breakout_evidence import analyze_breakout, build_evidence_board


def history(extra):
    rows = [[98, 100, 95, 99, 100]] * 250 + extra
    return pd.DataFrame(rows, columns=['Open', 'High', 'Low', 'Close', 'Volume'],
                        index=pd.bdate_range('2025-01-01', periods=len(rows)))


class EvidenceTests(unittest.TestCase):
    def test_intraday_break_is_not_close_break(self):
        e = analyze_breakout(history([[101, 110, 97, 99, 200]]))
        self.assertEqual(e['status'], '日中突破・終値未維持')
        self.assertEqual(e['events'], [])

    def test_volume_reference_excludes_today(self):
        e = analyze_breakout(history([[100, 110, 99, 108, 1000]]))
        self.assertEqual(e['today']['volume_ratio_prior20'], 10)

    def test_anchor_survives_higher_intraday_high(self):
        e = analyze_breakout(history([[100, 110, 99, 108, 200], [108, 112, 103, 105, 100]]))
        self.assertEqual(e['status'], '日中突破・終値未維持')
        self.assertEqual(e['latest_event']['reference_high'], 100)
        self.assertEqual(e['latest_event']['outcome'], '終値維持中')
        self.assertEqual(e['latest_event']['maintained_bars'], 1)

    def test_failed_event_is_not_erased_by_recovery(self):
        e = analyze_breakout(history([[100, 110, 99, 108, 200], [99, 100, 96, 97, 100],
                                     [100, 108, 99, 105, 100]]))
        self.assertEqual(e['latest_event']['outcome'], '終値割れ後に回復')
        self.assertEqual(e['latest_event']['maintained_bars'], 0)

    def test_same_high_not_break(self):
        self.assertEqual(analyze_breakout(history([[99, 100, 98, 100, 100]]))['status'],
                         '高値同値・未突破')

    def test_bad_data_not_promoted(self):
        d = history([[100, 110, 99, 108, 200]])
        d.iloc[-2, 2] = float('nan')
        self.assertFalse(analyze_breakout(d)['data_valid'])
        d = history([[100, 101, 99, 108, 200]])
        self.assertFalse(analyze_breakout(d)['data_valid'])

    def test_stale_date_quarantined(self):
        e = analyze_breakout(history([[100, 110, 99, 108, 200]]), expected_date='2026-10-14')
        b = build_evidence_board({'x': {'code': 'x', 'evidence': e}})
        self.assertEqual(len(b['unavailable']), 1)
        self.assertEqual(b['close_breaks'], [])

    def test_prefix_event_has_no_future_information(self):
        d = history([[100, 110, 99, 108, 200], [108, 109, 97, 98, 100]])
        before = analyze_breakout(d.iloc[:-1])['latest_event']
        after = analyze_breakout(d)['events'][0]
        self.assertEqual(before['outcome'], '当日・継続未確認')
        self.assertIsNone(before['first_close_below_date'])
        self.assertEqual(after['outcome'], '終値割れ')
        self.assertEqual(before['reference_high'], after['reference_high'])

    def test_flat_bar_no_nan_json(self):
        e = analyze_breakout(history([[101, 101, 101, 101, 100]]))
        self.assertIsNone(e['today']['close_location'])
        json.dumps(e, allow_nan=False)

    def test_daiichi_oct14_candle_with_known_prior_high(self):
        # Synthetic preceding history: tests the observed candle against 16800,
        # NOT a substitute for a full historical backtest.
        d = history([[16840, 17240, 16560, 16730, 179200]])
        d.iloc[:-1, :4] *= 168
        e = analyze_breakout(d)
        self.assertEqual(e['status'], '日中突破・終値未維持')
        self.assertAlmostEqual(e['today']['upper_wick_fraction'], 400/680)
        self.assertAlmostEqual(e['today']['close_location'], 170/680)


if __name__ == '__main__':
    unittest.main()
