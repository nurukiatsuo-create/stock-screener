import copy
import json
import unittest
from pathlib import Path
from audit_fundamentals import evaluate, build_report, evidence_key


class AuditTests(unittest.TestCase):
    def setUp(self):
        # Historical fixture must not change when live company evidence is updated.
        self.record = dict(code='6258', published_on='2026-11-13', checked_on='2026-11-14',
            period_end='2027-03-31', prior_period_end='2026-03-31',
            basis='annual_forecast_vs_prior_actual', comparable=True,
            operating_profit=10900, prior_operating_profit=8315, eps=261.2, prior_eps=198.54,
            source_url='https://www.hirata.co.jp/test-evidence.pdf')

    def poll(self, record=None, day='2026-11-14'):
        record = record or self.record
        return dict(code=record['code'], checked_on=day, success=True,
                    evidence_key=evidence_key(record), new_disclosure_found=False,
                    source_url='https://www.hirata.co.jp/ir/')

    def test_verified_annual_growth(self):
        r = evaluate(self.record, '2026-11-14', self.poll())
        self.assertEqual(r['assessment'], 'pass')
        self.assertTrue(r['eligible'])
        self.assertAlmostEqual(r['operating_profit_growth_pct'], 31.0884, places=4)

    def test_prior_assessment_survives_but_new_candidate_waits_for_poll(self):
        r = evaluate(self.record, '2026-11-15')
        self.assertEqual(r['assessment'], 'pass')
        self.assertEqual(r['freshness']['status'], 'unknown')
        self.assertFalse(r['eligible'])

    def test_new_poll_reuses_evidence_and_changes_invalidate_check(self):
        check = dict(code='6258', checked_on='2026-11-15', success=True,
                     evidence_key=evidence_key(self.record), new_disclosure_found=False,
                     source_url='https://www.hirata.co.jp/ir/')
        self.assertTrue(evaluate(self.record, '2026-11-15', check)['eligible'])
        check['new_disclosure_found'] = True
        self.assertEqual(evaluate(self.record, '2026-11-15', check)['freshness']['status'], 'superseded')
        check['new_disclosure_found'] = False
        self.record['operating_profit'] += 1
        self.assertFalse(evaluate(self.record, '2026-11-15', check)['eligible'])

    def test_missing_future_and_invalid_never_pass(self):
        self.assertEqual(evaluate(None, '2026-11-14')['assessment'], 'unknown')
        self.assertEqual(evaluate(self.record, '2026-11-12')['assessment'], 'unknown')
        for key, value in [('eps', float('nan')), ('comparable', False), ('prior_period_end', '2024-03-31'),
                           ('source_url', 'https://'), ('checked_on', '2026-11-12')]:
            record = copy.deepcopy(self.record); record[key] = value
            with self.subTest(key=key):
                self.assertEqual(evaluate(record, '2026-11-14')['assessment'], 'unknown')

    def test_quarterly_is_not_substituted_for_annual_forecast(self):
        record = dict(self.record, code='6871', published_on='2026-11-12',
                      period_end='2026-09-30', prior_period_end='2025-09-30',
                      basis='ytd_actual_vs_prior_ytd', operating_profit=26993,
                      prior_operating_profit=11300, eps=503.17, prior_eps=183.02)
        r = evaluate(record, '2026-11-14')
        self.assertEqual(r['numerical_status'], '数値条件合格')
        self.assertEqual(r['assessment'], 'review')
        self.assertFalse(r['eligible'])

    def test_low_growth_requires_explicit_exception_review(self):
        self.record['operating_profit'] = 9000
        self.assertEqual(evaluate(self.record, '2026-11-14')['assessment'], 'review')
        self.record['exception_review'] = dict(decision='approved', reviewed_on='2026-11-14',
            evidence_key=evidence_key(self.record), grounds=['upward_revision'], sustainable=True,
            source_url=self.record['source_url'], reason='テスト用の根拠付き例外承認')
        self.assertTrue(evaluate(self.record, '2026-11-14', self.poll())['eligible'])
        self.record['exception_review']['sustainable'] = False
        self.assertFalse(evaluate(self.record, '2026-11-14')['eligible'])
        self.record['exception_review']['decision'] = 'rejected'
        self.assertEqual(evaluate(self.record, '2026-11-14')['assessment'], 'fail')

    def test_approval_cannot_be_carried_to_changed_figures_or_future(self):
        self.record['eps'] = 190
        self.record['exception_review'] = dict(decision='approved', reviewed_on='2026-11-15',
            evidence_key=evidence_key(self.record), grounds=['record_profit'], sustainable=True,
            source_url=self.record['source_url'], reason='テスト例外')
        self.assertFalse(evaluate(self.record, '2026-11-14')['eligible'])
        self.record['exception_review']['reviewed_on'] = '2026-11-14'
        self.record['eps'] = 180
        self.assertFalse(evaluate(self.record, '2026-11-14')['eligible'])

    def test_zero_base_and_completed_forecast_need_review(self):
        self.record['prior_eps'] = 0
        self.assertEqual(evaluate(self.record, '2026-11-14')['assessment'], 'review')
        self.assertFalse(evaluate(self.record, '2027-04-01')['eligible'])

    def test_duplicate_evidence_rejected(self):
        with self.assertRaises(ValueError):
            build_report({'rows': []}, {'records': [self.record, self.record]}, '2026-11-14')

    def test_evidence_checked_today_never_replaces_an_actual_disclosure_check(self):
        self.record['checked_on'] = '2026-11-15'
        r = evaluate(self.record, '2026-11-15')
        self.assertEqual(r['assessment'], 'pass')
        self.assertEqual(r['freshness']['status'], 'unknown')
        self.assertFalse(r['eligible'])
        self.assertTrue(evaluate(self.record, '2026-11-15', self.poll(day='2026-11-15'))['eligible'])
        stale = evaluate(self.record, '2026-11-15', self.poll(day='2026-11-14'))
        self.assertFalse(stale['eligible'])
        self.assertEqual(stale['freshness']['checked_on'], '2026-11-14')


if __name__ == '__main__':
    unittest.main()
