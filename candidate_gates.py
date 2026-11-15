"""Explainable final selection. Unknown evidence never qualifies as a pass."""
import copy
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from audit_fundamentals import build_report, https_source
from market_calendar import expected_eod_date


def load_inputs(root):
    root = Path(root)
    def read(name, default):
        path = root/'audit'/name
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
    return {'shikiho': read('shikiho_candidates_2026.json', {'rows': []}),
            'fundamentals': read('fundamental_evidence.json', {'records': []}),
            'checks': read('disclosure_checks.json', {'records': []}),
            'topix': read('topix_membership.json', {})}


def gate(status, reason, **details):
    return dict(status=status, reason=reason, **details)


def finite_positive(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


def shikiho_gate(record, as_of):
    if not record:
        return gate('unknown', '四季報選定の根拠未登録')
    try:
        if (record.get('source_verified') is True and record.get('source_edition')
                and record.get('source_locator') and record.get('source_claim')
                and date.fromisoformat(record['verified_on']) <= date.fromisoformat(as_of)):
            return gate('pass', '四季報原本と選定根拠を確認済み')
    except (ValueError, TypeError, KeyError):
        pass
    return gate('unknown', '四季報抽出リスト登録済み・原本未照合')


def topix_gate(code, snapshot, as_of):
    """Complete official snapshot; missing lists are not equivalent to empty lists."""
    unknown = gate('unknown', 'TOPIX公式リスト未確認')
    try:
        cutoff = date.fromisoformat(as_of)
        pub = date.fromisoformat(snapshot['published_on'])
        checked = date.fromisoformat(snapshot['checked_on'])
        expiry = date.fromisoformat(snapshot['valid_until'])
        host = urlparse(snapshot['source_url']).hostname or ''
        if (snapshot.get('verified') is not True or snapshot.get('complete') is not True
                or not https_source(snapshot['source_url'])
                or not (host == 'jpx.co.jp' or host.endswith('.jpx.co.jp'))
                or not pub <= checked <= cutoff <= expiry):
            return unknown
        transition = snapshot['transition_codes']
        inclusions = snapshot['new_inclusions']
        if not isinstance(transition, list) or not isinstance(inclusions, list):
            return unknown
        # Prevent an incomplete/ambiguous registry from asserting a negative match.
        if not all(isinstance(c, str) and re.fullmatch(r'[0-9A-Z]{4}', c) for c in transition):
            return unknown
        inc_codes = [r['code'] for r in inclusions]
        if not all(isinstance(c, str) and re.fullmatch(r'[0-9A-Z]{4}', c) for c in inc_codes):
            return unknown
        if not all(pub <= date.fromisoformat(r['effective_on']) for r in inclusions):
            return unknown
        if (len(transition) != len(set(transition)) or len(inc_codes) != len(set(inc_codes))
                or set(transition) & set(inc_codes)):
            return unknown
        if code in transition:
            return gate('fail', 'TOPIX移行措置対象・新規候補から除外', classification='transition',
                        source_url=snapshot['source_url'])
        inclusion = next((r for r in inclusions if r['code'] == code), None)
        if inclusion:
            effective = date.fromisoformat(inclusion['effective_on'])
            # Priority describes a forthcoming/rebalancing-day event, not a
            # perpetual claim of index-fund inflows after implementation.
            label = 'new_inclusion' if cutoff <= effective else 'included'
            return gate('pass', 'TOPIX新規組み入れ' if label == 'new_inclusion' else 'TOPIX組み入れ実施済み',
                        classification=label, effective_on=effective.isoformat(), source_url=snapshot['source_url'])
        return gate('pass', 'TOPIX移行措置リスト非該当', classification='other', source_url=snapshot['source_url'])
    except (KeyError, TypeError, ValueError):
        return unknown


def liquidity_gate(row, config):
    minimum = config.get('selection_policy', {}).get('min_avg_turnover_5d_yen', 40000000)
    if not finite_positive(minimum):
        raise ValueError('min_avg_turnover_5d_yen must be positive')
    value = row.get('avg_turnover_5d_yen')
    if not finite_positive(value):
        return gate('unknown', '5日平均売買代金未取得')
    return gate('pass' if value >= minimum else 'fail',
                '流動性条件合格' if value >= minimum else '5日平均売買代金不足',
                average_yen=value, minimum_yen=minimum)


def position_size(price, available, risk_yen, avg_turnover, participation=0.01):
    """Reference size at close; recalculation at the actual entry price is required."""
    if not finite_positive(participation) or participation > 1:
        raise ValueError('max_order_turnover_fraction must be in (0, 1]')
    if not finite_positive(price) or not isinstance(available, (int, float)) or not math.isfinite(available) or available < 0:
        return {'status': '確認待ち', 'reason': '価格・利用可能資金未確認', 'shares': None}
    if risk_yen is None:
        return {'status': '確認待ち', 'reason': '1取引の許容損失額未設定', 'shares': None}
    if not finite_positive(risk_yen):
        raise ValueError('risk_per_trade_yen must be null or positive')
    if not finite_positive(avg_turnover):
        return {'status': '確認待ち', 'reason': '流動性データ未取得', 'shares': None}
    stop = price * .9
    limits = {'cash': available/price, 'risk': risk_yen/(price-stop),
              'liquidity': avg_turnover*participation/price}
    shares = math.floor((min(limits.values())+1e-9)/100)*100
    return {'status': '試算' if shares else '見送り', 'shares': shares, 'stop_price': stop,
            'cost_yen': shares*price, 'planned_loss_yen': shares*(price-stop),
            'limiting_factor': min(limits, key=limits.get),
            'note': '終値による個別上限試算。共同配分・注文ではない。約定価格で再計算。窓開け損失は超過し得る。'}


def apply_selection(strategy, inputs, config, as_of, price_data_date, expected_date=None):
    """Preserve technical observations and v3 schema, add mandatory selection v1."""
    date.fromisoformat(as_of)
    expected_date = expected_date or expected_eod_date(as_of)
    result = copy.deepcopy(strategy)
    source_rows = inputs['shikiho']['rows']
    source_codes = [str(r['code']) for r in source_rows]
    if len(source_codes) != len(set(source_codes)):
        raise ValueError('Duplicate Shikiho code')
    source = {str(r['code']): r for r in source_rows}
    report = build_report({'rows': source_rows}, inputs['fundamentals'], as_of, inputs['checks'])
    financials = {r['code']: r for r in report['rows']}
    result.update(selection_version=1, selection_as_of=as_of, price_data_date=price_data_date, expected_price_date=expected_date,
                  candidates=[], technical_candidates=[], pending=[], excluded=[])
    rows = []
    policy = config.get('selection_policy', {})
    for original in strategy['observations']:
        row = copy.deepcopy(original)
        code = str(row['code'])
        technical = bool(row.get('technical_candidate', row.get('candidate', False)))
        technical_status = row.get('technical_status', row.get('status', 'データ確認待ち'))
        # Screening new evidence against old prices is visible and never looks
        # like a historical backtest using evidence unavailable on price day.
        row.update(technical_candidate=technical, technical_status=technical_status, candidate=False)
        f = financials.get(code, {'assessment': 'unknown', 'eligible': False,
                                 'reason': '業績根拠未登録', 'freshness': {'status': 'unknown'}})
        fresh = f.get('freshness', {}).get('status') == 'current'
        fundamental = gate('pass' if f.get('eligible') else 'fail' if f['assessment'] == 'fail' and fresh else 'unknown',
                           f['reason'] if fresh or f['assessment'] in ('unknown', 'review') else
                           f['status']+'・追加開示の更新確認待ち',
                           assessment=f['assessment'], numerical_status=f.get('numerical_status'),
                           freshness=f.get('freshness'), source_url=f.get('evidence', {}).get('source_url'))
        b = row.get('box') or {}
        technical_valid = b.get('valid') is True and b.get('date') == price_data_date == expected_date and technical_status != 'データ確認待ち'
        gates = {'shikiho': shikiho_gate(source.get(code), as_of), 'fundamental': fundamental,
                 'topix': topix_gate(code, inputs['topix'], as_of), 'liquidity': liquidity_gate(row, config),
                 'price_data': gate('pass' if technical_valid else 'unknown',
                                    '確定日足の技術計算済み' if technical_valid else '株価データ確認待ち（期待日 '+expected_date+'）')}
        failures = [v['reason'] for v in gates.values() if v['status'] == 'fail']
        missing = [v['reason'] for v in gates.values() if v['status'] == 'unknown']
        ready = not failures and not missing
        row.update(gates=gates, selection_reasons=failures+missing, rank=None,
                   fundamental_check=fundamental['reason'], eligibility_ready=ready)
        if failures:
            row.update(selection_status='excluded', status='除外：'+failures[0])
        elif missing:
            row.update(selection_status='pending', status='確認待ち：'+missing[0])
        elif technical:
            rank = 'S' if gates['topix'].get('classification') == 'new_inclusion' else 'A'
            row.update(selection_status='candidate', status=rank+'候補・業績と技術条件を確認', candidate=True, rank=rank)
        else:
            row.update(selection_status='watch', status=technical_status)
        row['order_preview'] = position_size(row.get('close'), result.get('available_yen'),
                                             policy.get('risk_per_trade_yen'), row.get('avg_turnover_5d_yen'),
                                             policy.get('max_order_turnover_fraction', 0.01))
        # Keep the old field for v6, but it remains explicitly a capital ceiling.
        rows.append(row)
    result['observations'] = rows
    result['candidates'] = sorted((r for r in rows if r['candidate']), key=lambda r: (r['rank'], r['code']))
    result['technical_candidates'] = [r for r in rows if r['technical_candidate']]
    result['pending'] = [r for r in rows if r['selection_status'] == 'pending']
    result['excluded'] = [r for r in rows if r['selection_status'] == 'excluded']
    gates = ('shikiho', 'fundamental', 'topix', 'liquidity', 'price_data')
    result['selection_counts'] = {'observations': len(rows), 'source_universe': len(source),
        'not_calculated_codes': sorted(set(source)-{r['code'] for r in rows}),
        'technical_candidates': len(result['technical_candidates']),
        'final': dict(Counter(r['selection_status'] for r in rows)),
        'by_gate': {key: dict(Counter(r['gates'][key]['status'] for r in rows)) for key in gates},
        'technical_reasons': dict(Counter(reason for r in rows for reason in r.get('entry_reasons', []))),
        'technical_states': dict(Counter(r['technical_status'] for r in rows))}
    result['selection_policy'] = {'rule_version': 1, 'financial_basis': 'annual_forecast_vs_prior_actual',
        'counts_note': '各条件の件数は重複あり。finalは排他的。',
        'rank_note': 'SはTOPIX組み入れ実施日までの属性区分。期待収益・勝率の順位ではない。',
        'limitations': ['収益性のバックテスト未実施', '技術条件の数値閾値は独自の暫定値',
                       '追加開示チェックは根拠付き記録が必要。プログラム実行だけでは確認済みにしない。']}
    result['policy'] = '業績・四季報原本・TOPIX・流動性を確認後、初動の技術条件を満たすもののみ候補。注文は行わない。'
    eligible = {r['code'] for r in result['candidates']}
    for holding in result.get('holdings', []):
        holding['add_candidate'] = bool(holding.get('add_candidate') and str(holding['code']) in eligible)
    return result, report
