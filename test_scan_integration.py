"""Offline integration: all configured tickers, valid JSON and unavailable reporting."""
import contextlib
import datetime
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import scan


class ScanIntegrationTests(unittest.TestCase):
    def holding_scenario(self, downloaded_holding):
        dates = pd.bdate_range(end='2026-11-13', periods=300)
        valid = pd.DataFrame({'Open': [100.]*300, 'High': [101.]*300,
                              'Low': [99.]*300, 'Close': [100.]*300,
                              'Volume': [100000.]*300}, index=dates)
        cached = {'code': '7094', 'name': 'NexTone',
                  'evidence': scan.analyze_breakout(valid, expected_date='2026-11-13'),
                  'box_strategy': scan.analyze_boxes(valid), 'avg_turnover_5d_yen': 10000000.}
        position = {'code': '7094', 'buy_date': '2026-11-02', 'buy_price': 100.,
                    'shares': 100, 'box_lower': 90., 'box_upper': 110.}
        config = {'budget_yen': 1000000, 'positions': [position]}
        prior = {'data_date': '2026-11-13', 'updated_at': '11/13 16:10',
                 'breakout_board': {'watching': [cached]}}
        def extract(_, ticker):
            return downloaded_holding.copy() if ticker == '7094.T' else valid.copy()
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'trading_config.json').write_text(json.dumps(config))
            (root / 'stocks_data.json').write_text(json.dumps(prior, allow_nan=False))
            try:
                os.chdir(root)
                with (patch.object(scan, '__file__', str(root / 'scan.py')),
                      patch.object(scan, 'TICKERS', ['6652.T', '7094.T']),
                      patch.object(scan.yf, 'download', return_value=pd.DataFrame()),
                      patch.object(scan, 'extract_ticker_frame', side_effect=extract),
                      patch.object(scan, 'datetime') as clock,
                      contextlib.redirect_stdout(io.StringIO())):
                    clock.now.return_value = datetime.datetime(2026, 11, 15, 17,
                                                                tzinfo=ZoneInfo('Asia/Tokyo'))
                    scan.analyze_market()
                result = json.loads((root / 'stocks_data.json').read_text())
            finally:
                os.chdir(old_cwd)
        json.dumps(result, allow_nan=False)
        return result

    def test_same_day_cache_cannot_validate_nan_or_stale_holding_history(self):
        dates = pd.bdate_range(end='2026-11-13', periods=300)
        valid = pd.DataFrame({'Open': [100.]*300, 'High': [101.]*300,
                              'Low': [99.]*300, 'Close': [100.]*300,
                              'Volume': [100000.]*300}, index=dates)
        for label, raw in [('NaN download', valid * float('nan')),
                           ('stale download', valid.iloc[:-1])]:
            with self.subTest(label=label):
                result = self.holding_scenario(raw)
                holding = result['strategy']['holdings'][0]
                self.assertEqual(holding['status'], 'データ確認待ち')
                self.assertFalse(holding['add_candidate'])
                self.assertNotIn('close', holding)
                self.assertNotIn('pnl_yen', holding)
                self.assertEqual(result['price_fetch_summary']['cache_codes'], ['7094'])
                observation = next(row for row in result['strategy']['observations'] if row['code'] == '7094')
                self.assertEqual(observation['price_source'], 'cached_confirmed')
                self.assertTrue(observation['box']['valid'])

    def test_valid_current_download_keeps_holding_valuation(self):
        dates = pd.bdate_range(end='2026-11-13', periods=300)
        valid = pd.DataFrame({'Open': [100.]*300, 'High': [101.]*300,
                              'Low': [99.]*300, 'Close': [100.]*300,
                              'Volume': [100000.]*300}, index=dates)
        result = self.holding_scenario(valid)
        holding = result['strategy']['holdings'][0]
        self.assertEqual(holding['status'], '保有継続')
        self.assertEqual(holding['close'], 100.)
        self.assertEqual(holding['pnl_yen'], 0.)
        self.assertEqual(result['price_fetch_summary']['cache_codes'], [])

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

