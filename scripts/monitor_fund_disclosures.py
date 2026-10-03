"""Auditable EDINET discovery; never equates a filing with institutional buying."""
import argparse
import ast
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo('Asia/Tokyo')
CODE_URL = 'https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip'
API = 'https://api.edinet-fsa.go.jp/api/v2/'
LIMITATIONS = [
    '自動処理はEDINETの大量保有関連書類の発見と原資料収集まで。機関の買い増し確定ではありません。',
    '保有割合・株数・共同保有・貸借・投資目的と運用方針は本文の確認が必要です。',
    'ファンド月報・企業IR・投資理由と決算の照合は自動化しておらず、要確認です。',
    '取得範囲外の開示・5%以下の保有等は網羅できません。未検出は保有なしではありません。',
    '過去の訂正・取下げを含む全履歴台帳ではなく、指定日付範囲の取得時点スナップショットです。',
]


def now():
    return datetime.now(JST).isoformat(timespec='seconds')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def universe(path):
    """Read literal constants only; never import/execute the trading scanner."""
    constants = {}
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('TICKERS', 'STOCK_NAMES'):
                    constants[target.id] = ast.literal_eval(node.value)
    tickers = constants['TICKERS']
    if not tickers or any(not re.fullmatch(r'[0-9A-Z]{4}\.T', t) for t in tickers):
        raise ValueError('invalid TICKERS')
    if len(tickers) != len(set(tickers)):
        raise ValueError('duplicate TICKERS')
    return {t[:-2]: constants.get('STOCK_NAMES', {}).get(t, t) for t in tickers}


def code_mapping(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        files = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(files) != 1 or z.getinfo(files[0]).file_size > 20_000_000:
            raise ValueError('unexpected code list')
        lines = z.read(files[0]).decode('cp932').splitlines()
    reader = csv.DictReader(lines[1:])
    if not {'ＥＤＩＮＥＴコード', '証券コード'} <= set(reader.fieldnames or []):
        raise ValueError('code list schema changed')
    result = {}
    for row in reader:
        sec = row['証券コード'].strip()
        if re.fullmatch(r'[0-9A-Z]{4}0', sec):
            result[row['ＥＤＩＮＥＴコード']] = sec[:4]
    if not result:
        raise ValueError('empty code mapping')
    return result


def validate_list(payload, requested_day):
    meta = payload.get('metadata', {})
    if str(meta.get('status')) != '200':
        status = str(meta.get('status', payload.get('StatusCode', 'unknown')))
        safe_status = status if status.isdigit() else 'unknown'
        raise ValueError(f'EDINET response status={safe_status}')
    rows = payload.get('results')
    if not isinstance(rows, list):
        raise ValueError('EDINET results missing')
    if str(meta.get('resultset', {}).get('count')) != str(len(rows)):
        raise ValueError('EDINET result count mismatch')
    if meta.get('parameter', {}).get('date') != requested_day:
        raise ValueError('EDINET date mismatch')
    if any(not isinstance(row, dict) or not row.get('docID') for row in rows):
        raise ValueError('EDINET row schema changed')
    return rows


def match_filings(rows, mapping, watched):
    matches, unresolved = [], []
    for row in rows:
        if row.get('docTypeCode') not in ('350', '360'):
            continue
        # secCode is the FILER, not the investment target.
        issuer = row.get('issuerEdinetCode')
        code = mapping.get(issuer)
        if not code:
            unresolved.append(row)
        elif code in watched:
            matches.append(dict(row, target_code=code, target_name=watched[code]))
    return matches, unresolved


def cell(value):
    return str(value or '未確認').replace('|', '／').replace('\n', ' ')


def report(state, filings, watched):
    lines = ['# ファンド保有関連開示の確認', '',
             f"更新: {state['updated_at']} / 処理状態: **{state['status']}**",
             f"対象: {len(watched)}銘柄 / 取得済み: {len(state['completed_dates'])}/{len(state['requested_dates'])}日",
             f"対象期間: {state['window_start']} ～ {state['window_end']}（日本時間の日付）",
             f"研究判断: **未完了（原資料の精査待ち）** / 関連書類: {len(filings)}件", '',
             '## 制約', *['- ' + s for s in LIMITATIONS], '',
             '## 取得エラー・未確認', *['- ' + cell(s) for s in state['errors']],
             '- EDINETコード未対応銘柄: ' + ', '.join(state.get('unmapped_tickers', [])),
             f"- 発行会社を照合できない大量保有関連書類: {state.get('unresolved_count', 0)}件（unresolved.json参照）", '',
             '## 原資料の確認待ち',
             '| 銘柄 | 提出者 | 提出日時 | 書類 | 取下/不開示 | 本文 |',
             '|---|---|---|---|---|---|']
    for r in filings:
        url = 'https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100=' + r['docID']
        lines.append('| ' + ' | '.join(map(cell, [r['target_code'] + ' ' + r['target_name'],
            r.get('filerName'), r.get('submitDateTime'),
            f"[{r.get('docDescription') or r['docID']}]({url})",
            str(r.get('withdrawalStatus')) + '/' + str(r.get('disclosureStatus')),
            r.get('document_status', '未取得')])) + ' |')
    lines += ['', '## 銘柄別の確認範囲', '| 銘柄 | 関連書類数 | 保有増減・ファンド月報・企業IR |', '|---|---|---|']
    for code, name in watched.items():
        n = sum(r['target_code'] == code for r in filings)
        lines.append(f'| {code} {cell(name)} | {n} | 未確認 |')
    return '\n'.join(lines) + '\n'


class Client:
    def __init__(self, key, deadline):
        self.key, self.deadline = key, deadline

    def get(self, url, params=None):
        for attempt in range(3):
            if time.monotonic() > self.deadline:
                raise RuntimeError('調査時間上限に到達。未取得分を残して終了')
            time.sleep(1)
            request_url = url
            if params is not None:
                request_url += '?' + urllib.parse.urlencode(dict(params, **{'Subscription-Key': self.key}))
            try:
                with urllib.request.urlopen(request_url, timeout=30) as response:
                    data = response.read(30_000_001)
                if len(data) > 30_000_000:
                    raise RuntimeError('取得サイズ上限を超過')
                return data
            except urllib.error.HTTPError as exc:
                # Never log exception text: it may contain the API key in its URL.
                if exc.code in (401, 403):
                    raise PermissionError(f'EDINET認証エラー HTTP {exc.code}') from None
                if attempt == 2:
                    raise RuntimeError(f'HTTP {exc.code}') from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise RuntimeError('通信失敗（3回試行）') from None
            time.sleep(2 ** attempt)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['daily', 'weekly', 'baseline'], default='daily')
    parser.add_argument('--as-of', type=date.fromisoformat)
    parser.add_argument('--output', type=Path, default=Path('fund-monitor-output'))
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    end = args.as_of or (datetime.now(JST).date() - timedelta(days=1))
    if end >= datetime.now(JST).date():
        parser.error('--as-of must be before today in JST')
    days = {'daily': 3, 'weekly': 7, 'baseline': 90}[args.mode]
    start = end - timedelta(days=days - 1)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    watched, filings, unresolved = {}, {}, {}
    state = dict(status='running', started_at=now(), updated_at=now(), mode=args.mode,
                 window_start=str(start), window_end=str(end), requested_dates=dates,
                 completed_dates=[], errors=[], research_complete=False,
                 source_commit=os.getenv('GITHUB_SHA'), run_id=os.getenv('GITHUB_RUN_ID'))

    def checkpoint(message):
        state['updated_at'] = now()
        state['unresolved_count'] = len(unresolved)
        print(f"[{now()}] {message}", flush=True)
        records = sorted(filings.values(), key=lambda r: (r.get('submitDateTime') or '', r['docID']))
        write_json(out / 'status.json', state)
        write_json(out / 'filings.json', records)
        write_json(out / 'unresolved.json', list(unresolved.values()))
        (out / 'report.md').write_text(report(state, records, watched), encoding='utf-8')

    checkpoint('開始')
    try:
        watched = universe(root / 'scan.py')
        write_json(out / 'universe.json', watched)
        snapshot = root / 'stocks_data.json'
        if snapshot.exists():
            (out / 'screener_snapshot.json').write_bytes(snapshot.read_bytes())
        key = os.getenv('EDINET_API_KEY', '').strip()
        if not key:
            raise PermissionError('EDINET_API_KEY未設定。GitHub Actions Secretへの登録が必要')
        client = Client(key, time.monotonic() + 14 * 60)
        blob = client.get(CODE_URL)
        (out / 'edinet_codes.zip').write_bytes(blob)
        mapping = code_mapping(blob)
        state['unmapped_tickers'] = sorted(set(watched) - set(mapping.values()))
        if state['unmapped_tickers']:
            state['errors'].append('EDINETコード未対応銘柄あり')
        for i, day in enumerate(dates, 1):
            checkpoint(f'開示一覧取得 {i}/{days}: {day}')
            try:
                payload = json.loads(client.get(API + 'documents.json', {'date': day, 'type': 2}))
                rows = validate_list(payload, day)
                write_json(out / 'raw' / (day + '.json'), payload)
                matched, unknown = match_filings(rows, mapping, watched)
                for r in matched:
                    filings[r['docID']] = dict(r, retrieved_at=now(), list_date=day,
                                              holding_change=None, fund_strategy=None)
                for r in unknown:
                    unresolved[r['docID']] = r
                state['completed_dates'].append(day)
            except PermissionError:
                raise
            except Exception as exc:
                reason = str(exc) if type(exc) is ValueError else type(exc).__name__
                state['errors'].append(f'{day}: {reason}（一覧未確認）')
                if time.monotonic() > client.deadline:
                    break
        if unresolved:
            state['errors'].append('発行会社を照合できない大量保有関連書類あり。網羅性未確認')
        for i, r in enumerate(filings.values(), 1):
            checkpoint(f"本文取得 {i}/{len(filings)}: {r['target_code']} {r['docID']}")
            if r.get('withdrawalStatus') != '0' or r.get('disclosureStatus') not in ('0', '3'):
                r['document_status'] = '取下・不開示等のため保留'
                continue
            if r.get('pdfFlag') != '1':
                r['document_status'] = 'PDF提供なし・手動確認'
                continue
            try:
                pdf = client.get(API + 'documents/' + r['docID'], {'type': 2})
                if not pdf.startswith(b'%PDF'):
                    raise ValueError('not PDF')
                target = out / 'documents' / (r['docID'] + '.pdf')
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(pdf)
                r['document_status'] = 'PDF保存済・精査待ち'
                r['sha256'] = hashlib.sha256(pdf).hexdigest()
            except Exception as exc:
                r['document_status'] = '本文取得失敗'
                state['errors'].append(f"{r['docID']}: {type(exc).__name__}（本文未確認）")
        state['status'] = 'partial' if state['errors'] else 'collection_complete'
    except PermissionError as exc:
        state['status'] = 'blocked'
        state['errors'].append(str(exc))
    except Exception as exc:
        state['status'] = 'failed'
        state['errors'].append(type(exc).__name__ + '（詳細なURL・認証情報はログ出力しません）')
    state['finished_at'] = now()
    checkpoint('終了: ' + state['status'])
    return 0 if state['status'] == 'collection_complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())

