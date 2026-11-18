import copy
import json
import tempfile
import unittest
from pathlib import Path

from check_disclosure_updates import (
    canonical_link, check_one, extract_items, make_baseline, run_checks,
    validate_fetch_url,
)


class DisclosureUpdateTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(code='6258', published_on='2026-11-13', checked_on='2026-11-15',
                           period_end='2027-03-31', prior_period_end='2026-03-31',
                           basis='annual_forecast_vs_prior_actual', comparable=True,
                           operating_profit=125, prior_operating_profit=100,
                           eps=120, prior_eps=100,
                           source_url='https://www.hirata.co.jp/files/report.pdf?123=')
        self.source = dict(source_url='https://www.hirata.co.jp/ir/news/',
                           official_index_url='https://www.hirata.co.jp/ir/news/',
                           kind='html_links', minimum_items=3)
        self.html = ('<a href="/files/report.pdf?456=">2026年度 決算</a>'
                     '<a href="/files/previous.pdf">前回決算</a>'
                     '<a href="/files/meeting.pdf">説明会</a>')
        self.monitor = make_baseline(self.record, self.source, self.html, '2026-11-15')

    def check(self, text=None, monitor=None, record=None, day='2026-11-16'):
        return check_one(record or self.record, monitor or self.monitor, day,
                         fetcher=lambda url: self.html if text is None else text)

    def test_success_requires_actual_listing_and_exact_evidence_binding(self):
        result = self.check()
        self.assertTrue(result['success'])
        self.assertFalse(result['new_disclosure_found'])
        self.assertEqual(result['checked_on'], '2026-11-16')
        self.assertEqual(result['evidence_key'], self.monitor['baseline']['evidence_key'])

    def test_new_release_stays_blocked_until_baseline_review(self):
        original = copy.deepcopy(self.monitor)
        changed = self.html + '<a href="/files/downward_revision.pdf">業績予想の下方修正</a>'
        for day in ('2026-11-16', '2026-11-17'):
            result = self.check(text=changed, day=day)
            self.assertTrue(result['success'])
            self.assertTrue(result['new_disclosure_found'])
        self.assertEqual(self.monitor, original)

    def test_changed_title_or_removed_release_cannot_look_unchanged(self):
        self.assertTrue(self.check(text=self.html.replace('2026年度 決算', '決算訂正'))['new_disclosure_found'])
        self.assertFalse(self.check(text=self.html.replace('<a href="/files/report.pdf?456=">2026年度 決算</a>', ''))['success'])

    def test_changed_financial_figures_or_source_invalidates_baseline(self):
        for key, value in [('operating_profit', 126), ('source_url', 'https://www.hirata.co.jp/files/new.pdf')]:
            record = {**self.record, key: value}
            self.assertFalse(self.check(record=record)['success'])
        monitor = copy.deepcopy(self.monitor)
        monitor['source_url'] = 'https://www.hirata.co.jp/news/'
        self.assertFalse(self.check(monitor=monitor)['success'])

    def test_future_review_or_future_financial_release_never_passes(self):
        self.assertFalse(self.check(day='2026-11-14')['success'])
        self.assertFalse(self.check(record={**self.record, 'published_on': '2026-11-17'})['success'])

    def test_empty_dynamic_page_or_login_page_is_not_no_news(self):
        for html in ('<div id="ir-news"></div><script src="feed.js"></script>',
                     '<a href="/login">Login</a><a href="/about">About</a><a href="/help">Help</a>'):
            self.assertFalse(self.check(text=html)['success'])

    def test_network_failure_invalidates_the_daily_confirmation(self):
        def failed(url):
            raise OSError('HTTP 503')
        result = check_one(self.record, self.monitor, '2026-11-16', failed)
        self.assertFalse(result['success'])
        self.assertIsNone(result['new_disclosure_found'])
        self.assertIn('503', result['reason'])

    def test_missing_baseline_does_not_create_one(self):
        monitor = {key: value for key, value in self.monitor.items() if key != 'baseline'}
        self.assertFalse(self.check(monitor=monitor)['success'])
        self.assertNotIn('baseline', monitor)

    def test_baseline_tampering_and_company_mismatch_are_rejected(self):
        monitor = copy.deepcopy(self.monitor)
        monitor['baseline']['items'][0]['title'] = 'Changed without review'
        self.assertFalse(self.check(monitor=monitor)['success'])
        monitor = {**self.monitor, 'code': '3968'}
        self.assertFalse(self.check(monitor=monitor)['success'])

    def test_jsonp_is_parsed_as_data_and_xj_files_inherit_title_and_date(self):
        text = '// official feed\nwindow.handler({"item":[{"link":"//pdf.irpocket.com/x.pdf", "title":"上方修正", "published":"2026-11-12 15:30:00"}]});'
        items = extract_items(text, 'https://xml.irpocket.com/3968/feed.js', 'json_feed')
        self.assertEqual(items[0]['url'], 'https://pdf.irpocket.com/x.pdf')
        self.assertEqual(items[0]['published_on'], '2026-11-12')
        xj = {'items': [{'title': '通期予想', 'publishDate': '2026/11/13 15:30:00',
                         'files': [{'url': 'https://contents.xj-storage.jp/example.pdf'}]}]}
        items = extract_items(json.dumps(xj), 'https://www.xj-storage.jp/list', 'json_feed')
        self.assertEqual(items[0]['title'], '通期予想')
        with self.assertRaises(ValueError):
            extract_items('window.handler({}); dangerousCode();', self.source['source_url'], 'json_feed')

    def test_future_feed_disclosure_is_not_used_in_a_past_date(self):
        source = {**self.source, 'kind': 'json_feed'}
        rows = [{'title': str(i), 'published': '2026-11-13',
                 'link': url} for i, url in enumerate([
                     self.record['source_url'], '/old.pdf', '/slides.pdf'])]
        monitor = make_baseline(self.record, source, json.dumps({'item': rows}), '2026-11-15')
        rows.append({'title': 'future', 'published': '2026-11-17', 'link': '/future.pdf'})
        self.assertFalse(self.check(text=json.dumps({'item': rows}), monitor=monitor)['success'])

    def test_text_only_feed_notice_cannot_disappear_from_comparison(self):
        source = {**self.source, 'kind': 'json_feed'}
        rows = [{'title': str(i), 'published': '2026-11-13',
                 'link': url} for i, url in enumerate([
                     self.record['source_url'], '/old.pdf', '/slides.pdf'])]
        monitor = make_baseline(self.record, source, json.dumps({'item': rows}), '2026-11-15')
        rows.append({'title': '業績修正についてのお知らせ', 'published': '2026-11-16',
                     'content': '詳細は後日公開'})
        result = self.check(text=json.dumps({'item': rows}), monitor=monitor)
        self.assertTrue(result['success'])
        self.assertTrue(result['new_disclosure_found'])

    def test_pdf_cache_busters_are_ignored_but_document_query_identifiers_are_kept(self):
        base = self.source['source_url']
        self.assertEqual(canonical_link('/a.pdf?123=', base), canonical_link('/a.pdf?456=', base))
        self.assertNotEqual(canonical_link('/download?id=1', base), canonical_link('/download?id=2', base))
        self.assertNotEqual(canonical_link('/download.pdf?id=1', base), canonical_link('/download.pdf?id=2', base))

    def test_fetch_target_must_be_reviewed_https_source(self):
        for url in ('http://www.hirata.co.jp/ir/', 'https://localhost/ir/',
                    'https://www.hirata.co.jp.evil.example/ir/', 'https://user:pass@www.hirata.co.jp/ir/'):
            with self.assertRaises(ValueError):
                validate_fetch_url(url)

    def test_run_preserves_manual_unmonitored_checks_and_updates_failed_monitored_check(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = Path(directory) / 'audit'
            audit.mkdir()
            other = {**self.record, 'code': '6871'}
            manual = {'code': '6871', 'checked_on': '2026-11-15', 'success': True,
                      'method': 'manual_review', 'new_disclosure_found': False}
            (audit / 'fundamental_evidence.json').write_text(json.dumps({'records': [self.record, other]}))
            (audit / 'disclosure_monitors.json').write_text(json.dumps({'records': [self.monitor]}))
            (audit / 'disclosure_checks.json').write_text(json.dumps({'records': [manual]}))
            summary = run_checks(directory, '2026-11-16', lambda url: '<div>no disclosures loaded</div>')
            checks = json.loads((audit / 'disclosure_checks.json').read_text())['records']
            self.assertEqual(summary['failed'], 1)
            self.assertEqual(summary['unmonitored_codes'], ['6871'])
            self.assertEqual(next(row for row in checks if row['code'] == '6871'), manual)
            self.assertFalse(next(row for row in checks if row['code'] == '6258')['success'])


if __name__ == '__main__':
    unittest.main()
