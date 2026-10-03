import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location('monitor', Path(__file__).resolve().parents[1] / 'scripts/monitor_fund_disclosures.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class MonitorTests(unittest.TestCase):
    def test_matches_issuer_not_filer(self):
        rows = [dict(docID='S1000001', docTypeCode='350', issuerEdinetCode='E1', secCode='99990'),
                dict(docID='S1000002', docTypeCode='350', issuerEdinetCode='E2', secCode='78260')]
        matched, unknown = m.match_filings(rows, {'E1': '7826', 'E2': '9999'}, {'7826': 'target'})
        self.assertEqual([r['docID'] for r in matched], ['S1000001'])
        self.assertFalse(unknown)

    def test_correction_and_unknown_are_retained(self):
        rows = [dict(docID='S1000001', docTypeCode='360', issuerEdinetCode='E1', withdrawalStatus='2'),
                dict(docID='S1000002', docTypeCode='350', issuerEdinetCode=None)]
        matched, unknown = m.match_filings(rows, {'E1': '7826'}, {'7826': 'target'})
        self.assertEqual(matched[0]['withdrawalStatus'], '2')
        self.assertEqual(len(unknown), 1)

    def test_empty_list_requires_valid_metadata(self):
        good = {'metadata': {'status': '200', 'parameter': {'date': '2026-10-02'}, 'resultset': {'count': 0}}, 'results': []}
        self.assertEqual(m.validate_list(good, '2026-10-02'), [])
        for bad in ({}, dict(good, results=None), dict(good, metadata={'status': '401'})):
            with self.assertRaises(ValueError): m.validate_list(bad, '2026-10-02')
        with self.assertRaises(ValueError): m.validate_list(good, '2026-10-01')

    def test_ast_does_not_execute_scanner(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'scan.py'
            p.write_text('raise RuntimeError()\nTICKERS=["123A.T"]\nSTOCK_NAMES={"123A.T":"test"}\n')
            self.assertEqual(m.universe(p), {'123A': 'test'})

    def test_code_list_alphanumeric(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            z.writestr('codes.csv', 'metadata\nＥＤＩＮＥＴコード,証券コード\nE12345,123A0\n'.encode('cp932'))
        self.assertEqual(m.code_mapping(buf.getvalue()), {'E12345': '123A'})

    def test_missing_key_writes_blocked_report(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'EDINET_API_KEY': ''}):
            self.assertEqual(m.main(['--output', tmp]), 1)
            status = json.loads((Path(tmp) / 'status.json').read_text())
            self.assertEqual(status['status'], 'blocked')
            self.assertFalse(status['research_complete'])
            self.assertEqual(status['completed_dates'], [])
            self.assertTrue((Path(tmp) / 'report.md').exists())

    def test_end_to_end_collection_preserves_review_pending(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            rows = ['metadata', 'ＥＤＩＮＥＴコード,証券コード']
            rows += [f'E{i:05d},{c}0' for i, c in enumerate(m.universe(Path(m.__file__).resolve().parents[1] / 'scan.py'))]
            z.writestr('codes.csv', ('\n'.join(rows)).encode('cp932'))
        def fake_get(self, url, params=None):
            if params is None: return buf.getvalue()
            if 'date' in params:
                data = dict(metadata=dict(status='200', parameter={'date': params['date']}, resultset={'count': 1}),
                    results=[dict(docID='S1000001', docTypeCode='350', issuerEdinetCode='E00000',
                                  withdrawalStatus='0', disclosureStatus='0', pdfFlag='1')])
                return json.dumps(data).encode()
            return b'%PDF-1.4\nfixture'
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'EDINET_API_KEY': 'test'}), patch.object(m.Client, 'get', fake_get):
            self.assertEqual(m.main(['--output', tmp]), 0)
            status = json.loads((Path(tmp) / 'status.json').read_text())
            self.assertEqual(status['status'], 'collection_complete')
            self.assertFalse(status['research_complete'])
            records = json.loads((Path(tmp) / 'filings.json').read_text())
            self.assertEqual(len(records), 1)
            self.assertIsNone(records[0]['holding_change'])


if __name__ == '__main__':
    unittest.main()
