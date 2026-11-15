"""Point-in-time evidence assessment, independent of disclosure-check freshness."""
import argparse
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
EXCEPTION_GROUNDS = {'upward_revision', 'shikiho_revision', 'record_profit'}


def https_source(value):
    return isinstance(value, str) and urlparse(value).scheme == 'https' and bool(urlparse(value).hostname)


def evidence_key(record):
    """Bind an approval/check to the exact financial figures, not just a code."""
    import hashlib
    keys = ('code', 'published_on', 'period_end', 'prior_period_end', 'basis',
            'operating_profit', 'prior_operating_profit', 'eps', 'prior_eps', 'source_url')
    payload = {k: record.get(k) for k in keys}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def disclosure_freshness(record, as_of, check=None):
    """No successful poll is inferred from running this program."""
    out = {'status': 'unknown', 'checked_on': record.get('checked_on'),
           'reason': '追加開示の更新確認待ち'}
    try:
        cutoff = date.fromisoformat(as_of)
        published = date.fromisoformat(record['published_on'])
        checked = date.fromisoformat(record['checked_on'])
        if not published <= checked <= cutoff:
            return {**out, 'reason': '公表日・確認日の時系列を要確認'}
        if check:
            through = date.fromisoformat(check['checked_on'])
            if (check.get('success') is True and str(check.get('code')) == str(record['code'])
                    and check.get('evidence_key') == evidence_key(record)
                    and https_source(check.get('source_url')) and published <= through <= cutoff):
                checked = max(checked, through)
                out['checked_on'] = checked.isoformat()
                if check.get('new_disclosure_found') is True:
                    return {**out, 'status': 'superseded', 'reason': '新しい開示あり・業績再判定待ち'}
                if check.get('new_disclosure_found') is not False:
                    return out
            else:
                return {**out, 'reason': '開示確認失敗・根拠との対応不一致'}
        if checked == cutoff:
            return {**out, 'status': 'current', 'reason': '判定日までの追加開示確認済み'}
    except (KeyError, TypeError, ValueError):
        pass
    return out


def evaluate(record, as_of, check=None):
    result = {'status': '確認待ち', 'assessment': 'unknown', 'eligible': False,
              'reason': '根拠資料未登録', 'freshness': {'status': 'unknown'}}
    if not record:
        return result
    result['evidence'] = record
    try:
        cutoff = date.fromisoformat(as_of)
        published = date.fromisoformat(record['published_on'])
        checked = date.fromisoformat(record['checked_on'])
        end = date.fromisoformat(record['period_end'])
        prior_end = date.fromisoformat(record['prior_period_end'])
        if not published <= checked <= cutoff:
            raise ValueError('判定日より後の資料・確認、または公表前の確認は使用不可')
        basis = record['basis']
        if basis not in ('annual_forecast_vs_prior_actual', 'ytd_actual_vs_prior_ytd'):
            raise ValueError('比較基準不明')
        if not 330 <= (end-prior_end).days <= 400:
            raise ValueError('前年同期間との比較でない')
        if basis == 'ytd_actual_vs_prior_ytd' and end > published:
            raise ValueError('未終了期間の実績')
        if basis == 'annual_forecast_vs_prior_actual' and end < cutoff:
            raise ValueError('対象決算期が終了・最新の通期資料を要確認')
        if record.get('comparable') is not True or not https_source(record.get('source_url')):
            raise ValueError('比較可能性・出典の確認が必要')
        values = [record[k] for k in ('operating_profit', 'prior_operating_profit', 'eps', 'prior_eps')]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
            raise ValueError('数値欠測または非有限値')
        op, prev_op, eps, prev_eps = values
        result['freshness'] = disclosure_freshness(record, as_of, check)
        result['evidence_key'] = evidence_key(record)
        if prev_op <= 0 or prev_eps <= 0:
            result.update(status='例外審査', assessment='review', reason='赤字・ゼロ基準は成長率で評価せず個別確認')
            return result
        op_growth, eps_growth = (op/prev_op-1)*100, (eps/prev_eps-1)*100
        numeric_pass = op_growth >= 20-1e-9 and eps_growth > 0
        result.update(operating_profit_growth_pct=round(op_growth, 4),
                      eps_growth_pct=round(eps_growth, 4),
                      numerical_status='数値条件合格' if numeric_pass else '数値条件不合格')
        # Quarterly growth is supporting evidence, never an unnoticed substitute
        # for the primary annual-forecast rule.
        if basis != 'annual_forecast_vs_prior_actual':
            result.update(status='例外審査', assessment='review', reason='四半期累計の数値評価・通期会社予想の確認待ち')
            return result
        if numeric_pass:
            result.update(status='業績条件合格', assessment='pass', reason='通期営業利益前年比20%以上かつEPS増加')
        else:
            result.update(status='例外審査', assessment='review', reason='通常数値条件未達・上方修正等の例外を要確認')
            review = record.get('exception_review') or {}
            if review:
                reviewed = date.fromisoformat(review['reviewed_on'])
                valid = (published <= reviewed <= cutoff and review.get('evidence_key') == result['evidence_key']
                         and https_source(review.get('source_url')) and bool(str(review.get('reason', '')).strip()))
                grounds = review.get('grounds', [])
                if (valid and review.get('decision') == 'approved' and isinstance(grounds, list)
                        and grounds and set(grounds) <= EXCEPTION_GROUNDS
                        and review.get('sustainable') is True and op > 0 and eps > 0):
                    result.update(status='業績例外合格', assessment='pass', reason=review['reason'])
                elif valid and review.get('decision') == 'rejected':
                    result.update(status='業績不合格', assessment='fail', reason=review['reason'])
        result['eligible'] = result['assessment'] == 'pass' and result['freshness']['status'] == 'current'
    except (KeyError, TypeError, ValueError) as error:
        result.update(status='確認待ち', assessment='unknown', eligible=False, reason=str(error))
    return result


def build_report(universe, evidence, as_of, checks=None):
    date.fromisoformat(as_of)
    records = evidence.get('records', [])
    codes = [str(r['code']) for r in records]
    if len(codes) != len(set(codes)):
        raise ValueError('Duplicate evidence code: one active assessment per company is required')
    known = {str(r['code']) for r in universe['rows']}
    if set(codes)-known:
        raise ValueError('Evidence outside audited universe')
    check_rows = (checks or {}).get('records', [])
    check_codes = [str(r['code']) for r in check_rows]
    if len(check_codes) != len(set(check_codes)):
        raise ValueError('Duplicate disclosure check code')
    lookup = {str(r['code']): r for r in records}
    checked = {str(r['code']): r for r in check_rows}
    rows = [{'code': str(r['code']), 'name': r.get('source_name', r.get('name')),
             'in_runtime_universe': r.get('in_runtime_universe'),
             **evaluate(lookup.get(str(r['code'])), as_of, checked.get(str(r['code'])))}
            for r in universe['rows']]
    return {'version': 2, 'as_of': as_of,
            'rule': '通期会社予想OP前年比20%以上 AND EPS増加、または根拠付き例外承認。四半期実績は別審査。',
            'limitations': ['業績評価と追加開示の確認状況は別管理。未確認情報を推測で合格にしない。',
                           '日付単位の終日確認用。公表時刻がないため当日場中バックテストには使用不可。',
                           'TOPIX・四季報原本・価格出来高・流動性は候補統合で別判定。'],
            'counts': dict(Counter(r['status'] for r in rows)),
            'freshness_counts': dict(Counter(r['freshness']['status'] for r in rows)),
            'eligible_count': sum(r['eligible'] for r in rows), 'rows': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', required=True)
    args = parser.parse_args()
    universe = json.loads((ROOT/'audit/universe_audit.json').read_text())
    evidence = json.loads((ROOT/'audit/fundamental_evidence.json').read_text())
    check_path = ROOT/'audit/disclosure_checks.json'
    checks = json.loads(check_path.read_text()) if check_path.exists() else {}
    report = build_report(universe, evidence, args.as_of, checks)
    (ROOT/'audit/fundamental_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'counts': report['counts'], 'eligible_count': report['eligible_count']}, ensure_ascii=False))
