"""Check reviewed official IR listings without changing financial figures.

Baselines are registered after an actual evidence review. A scheduled run never
creates or advances them: any listing change keeps the company awaiting review.
Only the reviewed listing/feed is fetched; document links are compared, not run.
"""
import argparse
import hashlib
import ipaddress
import json
import re
import socket
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, getproxies
from zoneinfo import ZoneInfo

from audit_fundamentals import evidence_key


# These are the issuer sites and IR providers actually inspected for this task.
# Adding a new source requires reviewing its issuer-to-provider relationship.
APPROVED_FETCH_HOSTS = frozenset({
    'www.hirata.co.jp', 'xml.irpocket.com', 'www.xj-storage.jp',
    'www.sbiglobalam.co.jp', 'ssl4.eir-parts.net',
})
MAX_RESPONSE_BYTES = 5_000_000


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def canonical_link(value, base):
    """Ignore only numeric empty PDF cache-busters, preserving document IDs."""
    if not isinstance(value, str) or not value.strip() or value.startswith('#'):
        return None
    parsed = urlsplit(urljoin(base, value.strip()))
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return None
    query = parsed.query
    if parsed.path.lower().endswith('.pdf'):
        pairs = parse_qsl(query, keep_blank_values=True)
        query = urlencode([(key, item) for key, item in pairs if not (key.isdigit() and item == '')])
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, query, ''))


def validate_fetch_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in APPROVED_FETCH_HOSTS
            or parsed.port not in (None, 443) or parsed.username or parsed.password):
        raise ValueError('未登録の公式IR取得先、または安全でないURL')
    return parsed.hostname


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        # An unreviewed destination must not inherit an issuer's source approval.
        return None


def fetch_listing(url, timeout=15):
    host = validate_fetch_url(url)
    # Standard HTTPS proxies resolve issuer hosts themselves. The strict hostname
    # allowlist and disabled redirects apply on both direct and proxied routes.
    if not getproxies().get('https'):
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError('公開IP以外の取得先は使用不可')
    request = Request(url, headers={'User-Agent': 'StockScreener-IR-Monitor/1.0',
                                    'Accept': 'text/html,application/json,application/javascript,text/javascript'})
    with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError('IR一覧の取得に失敗')
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError('IR一覧の取得上限を超過')
        charset = response.headers.get_content_charset() or 'utf-8'
    return body.decode(charset, errors='strict')


class ListingLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.href = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.href = dict(attrs).get('href')
            self.text = []

    def handle_data(self, data):
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.href is not None:
            self.links.append((self.href, ' '.join(' '.join(self.text).split())))
            self.href = None
            self.text = []


def parse_feed(text):
    stripped = re.sub(r'^\s*(?://[^\n]*\n\s*)*', '', text).strip()
    if stripped.startswith(('{', '[')):
        return json.loads(stripped)
    match = re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\((.*)\)\s*;?\s*', stripped, re.S)
    if not match:
        raise ValueError('IRフィードのJSON/JSONP形式を確認できない')
    # JSONP is parsed as data. Never evaluate JavaScript from an issuer website.
    return json.loads(match.group(1))


def extract_items(text, source_url, kind):
    items = []
    if kind == 'html_links':
        parser = ListingLinks()
        parser.feed(text)
        for href, title in parser.links:
            link = canonical_link(href, source_url)
            if link:
                items.append({'url': link, 'title': title, 'published_on': None})
    elif kind == 'json_feed':
        payload = parse_feed(text)
        if not isinstance(payload, dict):
            raise ValueError('IRフィードの最上位はobjectが必要')
        rows = payload.get('items', payload.get('item'))
        if not isinstance(rows, list):
            raise ValueError('IRフィードの開示一覧を確認できない')
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('IRフィードの開示行が不正')
            title = ' '.join(str(row.get('title', '')).split())
            published = row.get('publishDate', row.get('published', row.get('date')))
            if not isinstance(published, str):
                raise ValueError('IRフィードの開示日が欠落')
            published = date.fromisoformat(published[:10].replace('/', '-')).isoformat()
            files = row.get('files')
            if files is None:
                files = [{'url': row.get('link', row.get('url'))}]
            if not isinstance(files, list):
                raise ValueError('IRフィードの資料一覧が不正')
            item_count_before = len(items)
            for entry in files:
                if not isinstance(entry, dict):
                    raise ValueError('IRフィードの資料URLが不正')
                link = canonical_link(entry.get('url', entry.get('link')), source_url)
                if link:
                    items.append({'url': link, 'title': title, 'published_on': published,
                                  'source_item_sha256': digest(row)})
            if len(items) == item_count_before:
                # Text-only notices are still disclosures. Silently dropping a
                # new no-link item would falsely report an unchanged feed.
                items.append({'url': None, 'title': title, 'published_on': published,
                              'source_item_sha256': digest(row)})
    else:
        raise ValueError('未対応の公式IR一覧形式')
    unique = {json.dumps(item, sort_keys=True, ensure_ascii=False): item for item in items}
    return [unique[key] for key in sorted(unique)]


def source_contract(monitor):
    return {key: monitor.get(key) for key in ('code', 'source_url', 'official_index_url', 'kind', 'minimum_items')}


def validate_items(items, monitor, record, as_of):
    minimum = monitor.get('minimum_items', 3)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 2:
        raise ValueError('一覧としての最小件数が不正')
    if len(items) < minimum:
        raise ValueError('開示一覧が空または不足。動的ページ未取得の可能性')
    document = canonical_link(record['source_url'], monitor['source_url'])
    if document not in {item['url'] for item in items}:
        raise ValueError('評価中の業績資料URLが公式一覧に存在しない')
    if any(item.get('published_on') and item['published_on'] > as_of for item in items):
        raise ValueError('判定日より後の開示を含む')


def make_baseline(record, source, text, reviewed_on):
    """Explicit review helper only; the scheduled CLI never invokes this function."""
    date.fromisoformat(reviewed_on)
    validate_fetch_url(source['source_url'])
    if date.fromisoformat(record['published_on']) > date.fromisoformat(reviewed_on):
        raise ValueError('公表前に基準一覧を承認できない')
    monitor = {**source, 'code': str(record['code']), 'enabled': True, 'official_source_verified': True}
    items = extract_items(text, monitor['source_url'], monitor['kind'])
    validate_items(items, monitor, record, reviewed_on)
    monitor['baseline'] = {'reviewed_on': reviewed_on, 'evidence_key': evidence_key(record),
                           'source_contract_sha256': digest(source_contract(monitor)),
                           'items_sha256': digest(items), 'items': items,
                           'note': 'この一覧を確認して基準登録。日次処理では自動更新しない。'}
    return monitor


def check_one(record, monitor, as_of, fetcher=fetch_listing):
    result = {'code': str(record['code']), 'checked_on': as_of, 'success': False,
              'checked_at': datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds'),
              'source_url': monitor.get('source_url'), 'evidence_key': evidence_key(record),
              'new_disclosure_found': None, 'method': 'official_ir_listing_diff_v1'}
    try:
        cutoff = date.fromisoformat(as_of)
        published = date.fromisoformat(record['published_on'])
        baseline = monitor['baseline']
        reviewed = date.fromisoformat(baseline['reviewed_on'])
        validate_fetch_url(monitor['source_url'])
        if (monitor.get('enabled') is not True or monitor.get('official_source_verified') is not True
                or str(monitor['code']) != str(record['code']) or not published <= reviewed <= cutoff):
            raise ValueError('公式取得先・銘柄・基準確認日の対応を要確認')
        if baseline['evidence_key'] != evidence_key(record):
            raise ValueError('業績数値または根拠資料が変更。基準一覧の再承認が必要')
        if baseline['source_contract_sha256'] != digest(source_contract(monitor)):
            raise ValueError('監視先または取得方法が変更。基準一覧の再承認が必要')
        if digest(baseline['items']) != baseline['items_sha256']:
            raise ValueError('基準一覧の整合性エラー')
        validate_items(baseline['items'], monitor, record, baseline['reviewed_on'])
        items = extract_items(fetcher(monitor['source_url']), monitor['source_url'], monitor['kind'])
        validate_items(items, monitor, record, as_of)
        current_hash = digest(items)
        changed = current_hash != baseline['items_sha256']
        previous = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in baseline['items']}
        current = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in items}
        result.update(success=True, new_disclosure_found=changed, baseline_reviewed_on=baseline['reviewed_on'],
                      observed_items_sha256=current_hash, observed_item_count=len(items),
                      added_or_changed_items=len(current - previous), removed_or_changed_items=len(previous - current),
                      reason='公式IR一覧に追加・変更あり。業績資料の再確認待ち' if changed else '公式IR一覧を実取得し、承認済み一覧との差分なし')
    except (KeyError, TypeError, ValueError, OSError, UnicodeError) as error:
        result['reason'] = str(error)
    return result


def run_checks(root, as_of, fetcher=fetch_listing):
    root = Path(root)
    audit = root / 'audit'
    evidence = json.loads((audit / 'fundamental_evidence.json').read_text())['records']
    if len({str(row['code']) for row in evidence}) != len(evidence):
        raise ValueError('Duplicate financial evidence code')
    registry = json.loads((audit / 'disclosure_monitors.json').read_text())
    monitor_rows = registry.get('records', [])
    if len({str(row['code']) for row in monitor_rows}) != len(monitor_rows):
        raise ValueError('Duplicate disclosure monitor code')
    monitor_map = {str(row['code']): row for row in monitor_rows}
    path = audit / 'disclosure_checks.json'
    prior = json.loads(path.read_text()) if path.exists() else {'version': 1, 'records': []}
    if len({str(row['code']) for row in prior['records']}) != len(prior['records']):
        raise ValueError('Duplicate disclosure check code')
    checks = {str(row['code']): row for row in prior['records']}
    updated = []
    unmonitored = []
    for record in evidence:
        code = str(record['code'])
        monitor = monitor_map.get(code)
        if not monitor or monitor.get('enabled') is not True:
            # Preserve a genuine manual check. No fabricated daily check is added.
            unmonitored.append(code)
            continue
        result = check_one(record, monitor, as_of, fetcher)
        checks[code] = result
        updated.append(result)
    output = {**prior, 'version': 1, 'records': [checks[code] for code in sorted(checks)]}
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)
    return {'as_of': as_of, 'checked': len(updated),
            'unchanged': sum(r['success'] and r['new_disclosure_found'] is False for r in updated),
            'changed': sum(r['success'] and r['new_disclosure_found'] is True for r in updated),
            'failed': sum(not r['success'] for r in updated), 'unmonitored_codes': unmonitored}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', default=datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat())
    arguments = parser.parse_args()
    today = datetime.now(ZoneInfo('Asia/Tokyo')).date().isoformat()
    if arguments.as_of != today:
        parser.error('Live IR polling can only record the current Japanese date.')
    print(json.dumps(run_checks(Path(__file__).resolve().parent, arguments.as_of), ensure_ascii=False))
