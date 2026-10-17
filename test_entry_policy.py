"""Regressions for aged boxes, event reset, volume and causal entry windows."""
import unittest
from box_strategy import analyze_boxes, build_strategy, entry_policy
from breakout_evidence import analyze_breakout
from test_box_strategy import sample, append


def evaluate(df, config=None):
    e = analyze_breakout(df, expected_date=str(df.index[-1].date()))
    return build_strategy({'7094': dict(name='test', evidence=e, box_strategy=analyze_boxes(df))}, config or {})['observations'][0]


class EntryPolicyTests(unittest.TestCase):
    def test_three_sessions_do_not_reset_on_daily_highs(self):
        d = append(sample(280),104,106.2,103,106,2000)
        self.assertTrue(evaluate(d)['candidate'])
        anchor = evaluate(d)['entry_event']['date']
        for close in (106.3,106.6):
            d = append(d,106,close+.1,105,close,1000)
            r = evaluate(d)
            self.assertTrue(r['candidate'])
            self.assertEqual(r['entry_event']['date'], anchor)
        d = append(d,106,107,105,106.9,5000)
        self.assertFalse(evaluate(d)['candidate'])
        self.assertIn('初動期間', ''.join(evaluate(d)['entry_reasons']))

    def test_flat_day_after_initial_break_remains_eligible(self):
        d = append(sample(280),104,106.5,103,106,2000)
        first = evaluate(d)
        later = append(d,106,106.3,105,106,800)
        self.assertTrue(evaluate(later)['candidate'])
        self.assertEqual(evaluate(d), first)

    def test_volume_is_first_event_not_later_volume(self):
        d = append(sample(280),104,106.2,103,106,1000)
        self.assertFalse(evaluate(d)['candidate'])
        d = append(d,106,107,105,106.5,5000)
        self.assertFalse(evaluate(d)['candidate'])
        self.assertIn('初回新高値突破の出来高不足', evaluate(d)['entry_reasons'])

    def test_gap_and_very_old_box_are_not_entries(self):
        d = append(sample(280),104,201,103,200,5000)
        self.assertFalse(evaluate(d)['candidate'])
        for _ in range(12):
            d = append(d,200,202,199,201,5000)
        self.assertFalse(evaluate(d)['candidate'])

    def test_return_failure_is_latched_after_recovery(self):
        d = append(sample(280),104,107,103,106,2000)
        d = append(d,105,106,90,103,1000)
        d = append(d,104,107,103,106,4000)
        r = evaluate(d)
        self.assertFalse(r['candidate'])
        self.assertTrue(r['box']['active_box']['return_date'])

    def test_near_break_watch_not_entry(self):
        r = evaluate(sample(280))
        self.assertFalse(r['candidate'])
        r = evaluate(sample(280), {'entry_policy': {'near_break_pct':10}})
        self.assertEqual(r['entry_group'],'pre_break')

    def test_limits_and_missing_metadata_fail_closed(self):
        d = append(sample(280),104,107,103,106,1500)
        self.assertTrue(evaluate(d)['candidate'])  # inclusive volume threshold
        e = analyze_breakout(d, expected_date=str(d.index[-1].date()))
        b = analyze_boxes(d)
        b['active_box'].pop('bars_since_breakout')
        r = build_strategy({'x':dict(name='x',evidence=e,box_strategy=b)}, {})
        self.assertEqual(r['candidates'],[])
        self.assertEqual(r['observations'][0]['status'],'データ確認待ち')
        for value in (0, -1, float('nan'), True, 2.5):
            with self.assertRaises(ValueError):
                entry_policy({'entry_policy':{'max_entry_bars':value}})
        with self.assertRaises(ValueError):
            entry_policy({'entry_policy':{'typo':3}})

    def test_7094_and_extended_screenshot_values(self):
        for code, close, upper, high, age in (
            ('7094',1912,1893.6483,2244.4121,0),
            ('3040',3550,1795,3500,30),
            ('5018',2983,1382,2900,30)):
            d = append(sample(280),104,107,103,106,2000)
            e = analyze_breakout(d, expected_date=str(d.index[-1].date()))
            b = analyze_boxes(d)
            b['active_box'].update(upper=upper,lower=upper*.9,bars_since_breakout=age)
            e['today'].update(close=close,reference_high=high)
            if code=='7094': e['events']=[]
            r=build_strategy({code:dict(name=code,evidence=e,box_strategy=b)}, {})
            self.assertEqual(r['candidates'],[])
            self.assertEqual(r['observations'][0]['entry_group'],'post_break')

if __name__ == '__main__': unittest.main()
