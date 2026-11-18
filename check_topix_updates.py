"""Detect unreviewed JPX announcements without accepting new index membership.

This checks the TOPIX page's news table, not every JPX disclosure or silent PDF
replacement. Operational fetch/parse failures produce an unknown result and
exit normally so the scanner can display the hold reason. Invalid local inputs
remain errors. Neither the baseline nor membership registry is changed.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests


SOURCE_URL = 'https://www.jpx.co.jp/markets/indices/topix/index.html'
ROOT = Path(__file__).resolve().parent


def _digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def snapshot_key(snapshot):
    """Bind a check to reviewed rules and source evidence, not lifecycle notes."""
    if not isinstance(snapshot, dict):
        raise ValueError('TOPIX snapshot must be an object')
    fields = ('version', 'verified', 'complete', 'source_url', 'published_on')
    value = {key: snapshot.get(key) for key in fields}
    transition = snapshot.get('transition_codes')
    additions = snapshot.get('new_inclusions')
    sources = snapshot.get('sources', [])
    if (not isinstance(transition, list) or not isinstance(additions, list)
            or not isinstance(sources, list)):
        raise ValueError('TOPIX snapshot lists are required')
    if not all(isinstance(code, str) for code in transition):
        raise ValueError('TOPIX transition codes must be strings')
    if not all(isinstance(row, dict) for row in additions + sources):
        raise ValueError('TOPIX source and inclusion rows must be objects')
    value['transition_codes'] = sorted(transition)
    value['new_inclusions'] = sorted(
        [{key: row.get(key) for key in ('code', 'effective_on', 'published_on', 'source_url')}
         for row in additions], key=lambda row: str(row['code']))
    value['sources'] = sorted(
        [{key: row.get(key) for key in ('source_url', 'published_on', 'effective_on', 'sha256')}
         for row in sources], key=lambda row: str(row['source_url']))
    return _digest(value)


def _jpx_url(url):
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    host = parsed.hostname or ''
    return (parsed.scheme == 'https' and not parsed.username and not parsed.password
            and (host == 'jpx.co.jp' or host.endswith('.jpx.co.jp')))


def _text(parts):
    return ' '.join(''.join(parts).split())


class NewsParseError(ValueError):
    """The downloaded page does not establish a complete news comparison."""


class _NewsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_heading = False
        self.heading = []
        self.awaiting_table = False
        self.in_table = False
        self.table_closed = False
        self.html_closed = False
        self.rows = []
        self.row = None
        self.field = None
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'h2':
            if self.awaiting_table:
                raise NewsParseError('関連ニュースの表が見つからない')
            self.in_heading, self.heading = True, []
        elif tag == 'table' and self.awaiting_table:
            self.in_table, self.awaiting_table = True, False
        elif tag == 'table' and self.in_table:
            raise NewsParseError('関連ニュース表に想定外の入れ子')
        elif self.in_table and tag == 'tr':
            if self.row is not None:
                raise NewsParseError('関連ニュースの行が閉じていない')
            self.row = {'date': [], 'links': []}
        elif self.row is not None and tag in ('th', 'td'):
            self.field = tag
        elif self.row is not None and self.field == 'td' and tag == 'a':
            if self.anchor is not None:
                raise NewsParseError('関連ニュースのリンクが不正')
            self.anchor = {'url': urljoin(SOURCE_URL, attrs.get('href', '')), 'title': []}

    def handle_data(self, data):
        if self.in_heading:
            self.heading.append(data)
        if self.row is not None and self.field == 'th':
            self.row['date'].append(data)
        if self.anchor is not None:
            self.anchor['title'].append(data)

    def handle_endtag(self, tag):
        if tag == 'h2' and self.in_heading:
            if _text(self.heading) == '関連ニュース':
                if self.table_closed or self.in_table:
                    raise NewsParseError('関連ニュースが複数あり曖昧')
                self.awaiting_table = True
            self.in_heading = False
        elif tag == 'a' and self.anchor is not None:
            self.anchor['title'] = _text(self.anchor['title'])
            self.row['links'].append(self.anchor)
            self.anchor = None
        elif tag in ('th', 'td'):
            self.field = None
        elif tag == 'tr' and self.in_table and self.row is not None:
            match = re.fullmatch(r'(\d{4})/(\d{1,2})/(\d{1,2})', _text(self.row['date']))
            links = self.row['links']
            if not match or len(links) != 1 or self.anchor is not None:
                raise NewsParseError('関連ニュースの日付・リンクを完全に解析できない')
            try:
                published = date(*map(int, match.groups())).isoformat()
            except ValueError as exc:
                raise NewsParseError('関連ニュースの日付が不正') from exc
            item = dict(links[0], published_on=published)
            if not _jpx_url(item['url']) or not item['title']:
                raise NewsParseError('関連ニュースの公式URL・見出しが不正')
            self.rows.append(item)
            self.row, self.field = None, None
        elif tag == 'table' and self.in_table:
            if self.row is not None:
                raise NewsParseError('関連ニュースの末尾が不完全')
            self.in_table, self.table_closed = False, True
        elif tag == 'html':
            self.html_closed = True


def parse_news(html):
    parser = _NewsParser()
    parser.feed(html)
    parser.close()
    if not parser.table_closed or not parser.html_closed or not parser.rows:
        raise NewsParseError('関連ニュースの全文・表を取得できない')
    urls = [row['url'] for row in parser.rows]
    if len(urls) != len(set(urls)):
        raise NewsParseError('関連ニュースのURLが重複')
    return parser.rows


def _validate_inputs(baseline, snapshot, as_of):
    cutoff = date.fromisoformat(as_of)
    if not isinstance(baseline, dict) or baseline.get('source_url') != SOURCE_URL:
        raise ValueError('Unexpected TOPIX news baseline source')
    checked = date.fromisoformat(baseline['checked_on'])
    floor = date.fromisoformat(baseline['announcement_floor'])
    if floor > checked:
        raise ValueError('TOPIX news baseline date order is invalid')
    if not re.fullmatch(r'[0-9a-f]{64}', baseline.get('snapshot_key', '')):
        raise ValueError('TOPIX news baseline needs its reviewed snapshot_key')
    known = baseline.get('known_announcements')
    if not isinstance(known, list) or not known:
        raise ValueError('TOPIX news baseline cannot be empty')
    urls = []
    for row in known:
        if (not isinstance(row, dict) or not _jpx_url(row.get('url'))
                or not isinstance(row.get('title'), str) or not row['title'].strip()
                or not floor <= date.fromisoformat(row['published_on']) <= checked):
            raise ValueError('Invalid approved TOPIX announcement')
        urls.append(row['url'])
    if len(urls) != len(set(urls)):
        raise ValueError('Duplicate approved TOPIX announcement')
    return cutoff, floor, checked, snapshot_key(snapshot)


def _result(baseline, key, as_of, status, reason, urls=()):
    return {'version': 1, 'source_url': SOURCE_URL, 'checked_on': as_of,
            'snapshot_key': key, 'baseline_key': _digest(baseline),
            'status': status, 'verified': status == 'verified',
            'success': status != 'unknown',
            'new_announcement_found': None if status == 'unknown' else status == 'changed',
            'reason': reason, 'urls': sorted(set(urls)),
            'scope': 'TOPIX公式ページの関連ニュース欄。銘柄の自動採用・期限延長は行わない。'}


def evaluate_news(html, baseline, snapshot, as_of):
    cutoff, floor, checked, key = _validate_inputs(baseline, snapshot, as_of)
    if checked > cutoff:
        return _result(baseline, key, as_of, 'unknown', '基準の確認日が判定日より後')
    if key != baseline['snapshot_key']:
        return _result(baseline, key, as_of, 'unknown', 'TOPIX根拠データ変更・ニュース基準の再確認待ち')
    try:
        news = parse_news(html)
        if any(date.fromisoformat(row['published_on']) > cutoff for row in news):
            raise NewsParseError('判定日より後の公表を含むため時点照合不能')
    except (NewsParseError, UnicodeError) as exc:
        return _result(baseline, key, as_of, 'unknown', str(exc))
    current = {row['url']: row for row in news if date.fromisoformat(row['published_on']) >= floor}
    known = {row['url']: row for row in baseline['known_announcements']}
    if not current or not set(known).issubset(current):
        return _result(baseline, key, as_of, 'unknown', '承認済みニュースの全部を再取得できない', current)
    changed = [url for url, row in current.items() if url not in known or row != known[url]]
    if changed:
        return _result(baseline, key, as_of, 'changed', 'TOPIX新公表・既存公表の変更を検知、再審査待ち', changed)
    result = _result(baseline, key, as_of, 'verified', '登録済みTOPIXニュースから新公表・見出し変更なし', current)
    result['announcements_compared'] = len(current)
    return result


def check_updates(baseline, snapshot, as_of, get=requests.get):
    _, _, _, key = _validate_inputs(baseline, snapshot, as_of)
    for attempt in range(1, 3):
        try:
            response = get(SOURCE_URL, timeout=(5, 20))
            response.raise_for_status()
            if not _jpx_url(response.url):
                raise NewsParseError('JPX公式ページ以外へ遷移')
            html = response.content.decode('utf-8-sig')
            break
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == 1:
                continue
            return _result(baseline, key, as_of, 'unknown', '公式ニュース取得失敗: '+type(exc).__name__)
        except (requests.RequestException, NewsParseError, UnicodeError) as exc:
            return _result(baseline, key, as_of, 'unknown', '公式ニュース取得失敗: '+type(exc).__name__)
    result = evaluate_news(html, baseline, snapshot, as_of)
    result['page_sha256'] = hashlib.sha256(response.content).hexdigest()
    result['network_attempts'] = attempt
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT/'audit/topix_membership.json')
    parser.add_argument('--baseline', type=Path, default=ROOT/'audit/topix_news_baseline.json')
    parser.add_argument('--output', type=Path, default=ROOT/'audit/topix_update_check.json')
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
    snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))
    as_of = datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat()
    result = check_updates(baseline, snapshot, as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=args.output.parent,
                                     delete=False, suffix='.tmp') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        temporary = stream.name
    os.replace(temporary, args.output)
    print(f"TOPIX更新確認: {result['status']} / {result['reason']}")


if __name__ == '__main__':
    main()
