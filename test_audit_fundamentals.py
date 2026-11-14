import copy
import json
import unittest
from pathlib import Path
from audit_fundamentals import evaluate, build_report

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.record=json.loads((Path(__file__).parent/'audit/fundamental_evidence.json').read_text())['records'][0]
    def test_verified_growth(self):
        r=evaluate(self.record,'2026-11-14')
        self.assertEqual(r['status'],'数値条件合格')
        self.assertAlmostEqual(r['operating_profit_growth_pct'],31.0884,places=4)
    def test_missing_does_not_pass(self):
        self.assertEqual(evaluate(None,'2026-11-14')['status'],'確認待ち')
    def test_future_evidence_blocked(self):
        self.assertEqual(evaluate(self.record,'2026-11-12')['status'],'確認待ち')
    def test_stale_check_blocked(self):
        self.assertEqual(evaluate(self.record,'2026-11-15')['status'],'確認待ち')
    def test_invalid_data(self):
        for key,value in [('prior_eps',0),('prior_operating_profit',-1),('eps',float('nan')),('comparable',False),('prior_period_end','2024-03-31')]:
            r=copy.deepcopy(self.record);r[key]=value
            with self.subTest(key=key):self.assertEqual(evaluate(r,'2026-11-14')['status'],'確認待ち')
    def test_eps_decline_fails(self):
        self.record['eps']=190
        self.assertEqual(evaluate(self.record,'2026-11-14')['status'],'数値条件不合格')
    def test_duplicate_evidence_rejected(self):
        with self.assertRaises(ValueError):
            build_report({'rows':[]},{'records':[self.record,self.record]},'2026-11-14')

if __name__=='__main__':unittest.main()
