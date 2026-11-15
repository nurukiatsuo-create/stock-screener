"""Offline integration: all configured tickers, valid JSON and unavailable reporting."""
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

    def test_short_history_is_reported_without_nonfinite_json(self):
        dates = pd.bdate_range('2026-11-09', periods=4)
        short = pd.DataFrame({'Open':[100.]*4,'High':[101.]*4,'Low':[99.]*4,
                              'Close':[100.]*4,'Volume':[1000.]*4}, index=dates)
        dates = pd.bdate_range('2025-01-01', periods=300)
        full = pd.DataFrame({'Open':[100.]*300,'High':[101.]*300,'Low':[99.]*300,
                             'Close':[100.]*300,'Volume':[1000.]*300}, index=dates)
        def extract(_, ticker):
            return short.copy() if ticker == scan.TICKERS[0] else full.copy()
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                with patch.object(scan.yf, 'download', return_value=pd.DataFrame()), patch.object(scan, 'extract_ticker_frame', side_effect=extract), contextlib.redirect_stdout(io.StringIO()):
                    scan.analyze_market()
                with open('stocks_data.json') as f:
                    result=json.load(f)
            finally:
                os.chdir(old_cwd)
        json.dumps(result,allow_nan=False)
        row=next(r for r in result['strategy']['observations'] if r['code']==scan.clean_code(scan.TICKERS[0]))
        self.assertIsNone(row['avg_turnover_5d_yen'])
        self.assertFalse(row['candidate'])

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
        self.assertIn('strategy', result)
        self.assertEqual(result['strategy']['selection_version'], 1)
        self.assertEqual(result['strategy']['selection_counts']['source_universe'], 112)
        self.assertEqual(result['strategy']['selection_counts']['not_calculated_codes'], [])
        self.assertTrue(all(not r['candidate'] for r in result['strategy']['observations']))
        self.assertEqual(result['strategy']['budget_yen'], 1000000)
        self.assertEqual(result['strategy']['candidates'], [])
        self.assertEqual(len(result['strategy']['observations']), len(scan.TICKERS))
        json.dumps(result, allow_nan=False)
        board = result['breakout_board']
        self.assertEqual(len(board['close_breaks']), len(scan.TICKERS)-1)
        self.assertEqual(len(board['unavailable']), 1)
        self.assertEqual(board['unavailable'][0]['code'], scan.clean_code(scan.TICKERS[0]))
        self.assertEqual(len(result['new_high_ranks']), len(scan.TICKERS)-1)
        self.assertTrue(all(r['nh_score'] == 90 for r in result['new_high_ranks']))
        self.assertTrue(all(r['evidence']['buy_signal'] is None for r in board['close_breaks']))


if __name__ == '__main__':
    unittest.main()

