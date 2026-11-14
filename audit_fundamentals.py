"""Evidence-based numerical growth audit; no trading signal or legacy score reuse."""
import argparse
import json
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def evaluate(record, as_of):
    result = {'status': '確認待ち', 'reason': '根拠資料未登録'}
    if not record:
        return result
    result['evidence'] = record
    try:
        cutoff = date.fromisoformat(as_of)
        published = date.fromisoformat(record['published_on'])
        checked = date.fromisoformat(record['checked_on'])
        end = date.fromisoformat(record['period_end'])
        prior_end = date.fromisoformat(record['prior_period_end'])
        if published > cutoff or checked > cutoff:
            raise ValueError('判定日より後の公表・確認資料は使用不可')
        if checked != cutoff:
            raise ValueError('当日までの追加開示確認が必要')
        if record['basis'] not in ('annual_forecast_vs_prior_actual', 'ytd_actual_vs_prior_ytd'):
            raise ValueError('比較基準不明')
        if not 330 <= (end-prior_end).days <= 400:
            raise ValueError('前年同期との比較でない')
        if record['basis'] == 'ytd_actual_vs_prior_ytd' and end > published:
            raise ValueError('未終了期間の実績')
        if record.get('comparable') is not True or not record.get('source_url', '').startswith('https://'):
            raise ValueError('比較可能性・出典の確認が必要')
        values = [record[k] for k in ('operating_profit','prior_operating_profit','eps','prior_eps')]
        if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values):
            raise ValueError('数値欠測または非有限値')
        op, prev_op, eps, prev_eps = values
        if prev_op <= 0 or prev_eps <= 0:
            raise ValueError('赤字・ゼロ基準は成長率で評価せず個別確認')
        op_growth = (op/prev_op-1)*100
        eps_growth = (eps/prev_eps-1)*100
        passed = op_growth >= 20-1e-9 and eps_growth > 0
        result.update(status='数値条件合格' if passed else '数値条件不合格',
                      reason='営業利益前年比20%以上かつEPS増加' if passed else '営業利益20%以上・EPS増加の同時条件を満たさない',
                      operating_profit_growth_pct=round(op_growth,4), eps_growth_pct=round(eps_growth,4))
    except (KeyError,TypeError,ValueError) as error:
        result['reason'] = str(error)
    return result


def build_report(universe, evidence, as_of):
    date.fromisoformat(as_of)
    records = evidence['records']
    codes = [r['code'] for r in records]
    if len(codes) != len(set(codes)):
        raise ValueError('Duplicate evidence code')
    known = {r['code'] for r in universe['rows']}
    if set(codes)-known:
        raise ValueError('Evidence outside audited universe')
    lookup = {r['code']:r for r in records}
    rows = [{'code':r['code'], 'name':r['source_name'],
             'in_runtime_universe':r['in_runtime_universe'],
             **evaluate(lookup.get(r['code']),as_of)} for r in universe['rows']]
    counts = {s:sum(r['status']==s for r in rows) for s in ('数値条件合格','数値条件不合格','確認待ち')}
    return {'version':1,'as_of':as_of,'rule':'OP前年比20%以上 AND EPS前年比プラス。実績・予想の基準を各行に明示。',
            'limitations':['成長率の一次判定のみ。四季報原本確認・利益の持続性・ROE・TOPIX・価格出来高判定は別工程。',
                            '上方修正・最高益による例外通過は未実装。数値条件不合格は最終除外を意味しない。',
                            '公表時刻未登録のため売買バックテストへの転用不可。checked_onは人による開示確認日。',
                            '現行Scriptable・売買候補には未接続。'],
            'counts':counts,'rows':rows}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--as-of',required=True)
    args=parser.parse_args()
    universe=json.loads((ROOT/'audit/universe_audit.json').read_text())
    evidence=json.loads((ROOT/'audit/fundamental_evidence.json').read_text())
    report=build_report(universe,evidence,args.as_of)
    (ROOT/'audit/fundamental_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['counts'],ensure_ascii=False))
