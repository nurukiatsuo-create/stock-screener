"""Offline integration: all 80 tickers, valid JSON and unavailable reporting."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
import scan


class ScanIntegrationTests(unittest.TestCase):
    def test_total_download_failure_preserves_previous_output(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                with open('stocks_data.json', 'w') as f:
                    f.write('{"previous":true}')
                with patch.object(scan.yf, 'download', return_value=pd.DataFrame()), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(RuntimeError):
                        scan.analyze_market()
                with open('stocks_data.json') as f:
                    self.assertEqual(json.load(f), {"previous": True})
            finally:
                os.chdir(old_cwd)

    def test_all_tickers_and_failed_download_are_reported(self):
        dates = pd.bdate_range('2025-01-01', periods=300)
        frame = pd.DataFrame({'Open': [1000.]*300, 'High': [1010.]*300,
                              'Low': [990.]*300, 'Close': [1005.]*300,
                              'Volume': [100000.]*300}, index=dates)
        frame.iloc[-1] = [1010, 1040, 1000, 1030, 200000]
        data = pd.concat({t: frame.copy() for t in scan.TICKERS[1:]}, axis=1)
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                with patch.object(scan.yf, 'download', return_value=data), contextlib.redirect_stdout(io.StringIO()):
                    scan.analyze_market()
                with open('stocks_data.json') as f:
                    result = json.load(f)
            finally:
                os.chdir(old_cwd)
        json.dumps(result, allow_nan=False)
        board = result['breakout_board']
        self.assertEqual(len(board['close_breaks']), 79)
        self.assertEqual(len(board['unavailable']), 1)
        self.assertEqual(board['unavailable'][0]['code'], scan.clean_code(scan.TICKERS[0]))
        self.assertEqual(len(result['new_high_ranks']), 79)
        self.assertTrue(all(r['nh_score'] == 90 for r in result['new_high_ranks']))
        self.assertTrue(all(r['evidence']['buy_signal'] is None for r in board['close_breaks']))


if __name__ == '__main__':
    unittest.main()
