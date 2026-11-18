"""Review boundaries for the read-only daily TOPIX announcement check."""
import copy
import unittest
from unittest.mock import Mock

import requests

from check_topix_updates import SOURCE_URL, check_updates, evaluate_news, snapshot_key


def fixture():
    snapshot = dict(version=1, verified=True, complete=True,
                    source_url='https://www.jpx.co.jp/news/topix.pdf',
                    published_on='2026-10-07', checked_on='2026-11-15',
                    valid_until='2026-11-29', transition_codes=['1234'],
                    new_inclusions=[], sources=[])
    rows = [dict(published_on='2026-11-09', url='https://www.jpx.co.jp/news/20261109.html',
                 title='TOPIXの構成銘柄への追加について'),
            dict(published_on='2026-10-07', url='https://www.jpx.co.jp/news/20261007.html',
                 title='TOPIX定期入替')]
    baseline = dict(source_url=SOURCE_URL, checked_on='2026-11-15',
                    announcement_floor='2026-10-07', known_announcements=rows,
                    snapshot_key=snapshot_key(snapshot))
    return baseline, snapshot


def page(rows):
    body = ''.join(f'<tr><th>{r["published_on"].replace("-", "/")}<br></th>'
                   f'<td><a href="{r["url"]}">{r["title"]}</a></td></tr>' for r in rows)
    return '<html><body><h2>関連ニュース</h2><table><tbody>'+body+'</tbody></table></body></html>'


class TopixNewsTests(unittest.TestCase):
    def setUp(self):
        self.baseline, self.snapshot = fixture()
        self.rows = copy.deepcopy(self.baseline['known_announcements'])

    def evaluate(self, html=None, as_of='2026-11-15'):
        return evaluate_news(page(self.rows) if html is None else html,
                             self.baseline, self.snapshot, as_of)

    def test_reviewed_news_are_current_without_mutating_the_registry(self):
        before = copy.deepcopy(self.snapshot)
        result = self.evaluate()
        self.assertEqual(result['status'], 'verified')
        self.assertTrue(result['success'])
        self.assertFalse(result['new_announcement_found'])
        self.assertEqual(self.snapshot, before)

    def test_new_or_changed_announcement_requires_review(self):
        self.rows.insert(0, dict(published_on='2026-11-15',
                              url='https://www.jpx.co.jp/news/new.html', title='追加発表'))
        result = self.evaluate()
        self.assertEqual(result['status'], 'changed')
        self.assertTrue(result['new_announcement_found'])
        self.assertIn(self.rows[0]['url'], result['urls'])
        self.rows = copy.deepcopy(self.baseline['known_announcements'])
        self.rows[0]['title'] += '（訂正）'
        self.assertEqual(self.evaluate()['status'], 'changed')

    def test_empty_partial_and_missing_known_news_never_confirm_no_change(self):
        for html in ('', '<html><body>アクセスできません</body></html>',
                     page(self.rows).replace('</table>', ''), page(self.rows[:1])):
            with self.subTest(html=html[:30]):
                result = self.evaluate(html)
                self.assertEqual(result['status'], 'unknown')
                self.assertFalse(result['success'])
                self.assertIsNone(result['new_announcement_found'])

    def test_changed_registry_cannot_reuse_an_old_approval(self):
        self.snapshot['transition_codes'].append('5678')
        result = self.evaluate()
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('根拠データ変更', result['reason'])

    def test_check_date_and_publication_boundary_prevent_future_information(self):
        self.assertEqual(self.evaluate(as_of='2026-11-14')['status'], 'unknown')
        self.rows.insert(0, dict(published_on='2026-11-16',
                              url='https://www.jpx.co.jp/news/new.html', title='追加発表'))
        self.assertEqual(self.evaluate()['status'], 'unknown')
        self.assertEqual(self.evaluate(as_of='2026-11-16')['status'], 'changed')

    def test_network_failure_is_an_unknown_result(self):
        get = Mock(side_effect=requests.Timeout('timeout'))
        result = check_updates(self.baseline, self.snapshot, '2026-11-15', get=get)
        self.assertEqual(result['status'], 'unknown')
        self.assertFalse(result['success'])
        self.assertEqual(get.call_count, 2)

    def test_one_transient_timeout_gets_a_bounded_retry(self):
        response = Mock(url=SOURCE_URL, content=page(self.rows).encode())
        get = Mock(side_effect=[requests.Timeout('timeout'), response])
        result = check_updates(self.baseline, self.snapshot, '2026-11-15', get=get)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['network_attempts'], 2)

    def test_invalid_baseline_is_not_silently_accepted(self):
        self.baseline['known_announcements'] = []
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_lifecycle_dates_do_not_redefine_the_source_evidence(self):
        original = snapshot_key(self.snapshot)
        self.snapshot.update(checked_on='2026-11-16', valid_until='2026-11-30', note='補足')
        self.assertEqual(snapshot_key(self.snapshot), original)


if __name__ == '__main__':
    unittest.main()
