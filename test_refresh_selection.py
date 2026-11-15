import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from refresh_selection import refresh
from test_candidate_gates import fixture


class RefreshTests(unittest.TestCase):
    def test_prices_and_their_timestamp_are_not_relabelled_by_audit_refresh(self):
        strategy, inputs, config = fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root/'audit').mkdir()
            for key, file in [('shikiho', 'shikiho_candidates_2026.json'), ('fundamentals', 'fundamental_evidence.json'),
                              ('checks', 'disclosure_checks.json'), ('topix', 'topix_membership.json')]:
                (root/'audit'/file).write_text(json.dumps(inputs[key]))
            (root/'trading_config.json').write_text(json.dumps(config))
            data = {'data_date':'2026-11-13','updated_at':'11/13 18:00','strategy':strategy,'untouched':[1,2,3]}
            path=root/'stocks_data.json'; path.write_text(json.dumps(data))
            refresh(root,'2026-11-13',datetime.fromisoformat('2026-11-13T20:00:00+09:00'))
            result=json.loads(path.read_text())
            self.assertEqual(result['updated_at'],data['updated_at'])
            self.assertEqual(result['data_date'],data['data_date'])
            self.assertEqual(result['untouched'],data['untouched'])
            self.assertEqual(result['strategy']['candidates'][0]['rank'],'A')
            first=path.read_text()
            (root/'audit/topix_membership.json').write_text('{invalid')
            with self.assertRaises(json.JSONDecodeError):refresh(root,'2026-11-13')
            self.assertEqual(path.read_text(),first)
            with self.assertRaises(ValueError):refresh(root,'2026-11-12')


if __name__=='__main__':unittest.main()
