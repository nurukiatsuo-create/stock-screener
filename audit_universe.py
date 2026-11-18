"""Audit source lineage without importing/executing scan.py or requesting prices."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def assignments(text):
    result = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'TICKERS', 'STOCK_NAMES', 'FUND_SCORES'}:
                    result[target.id] = ast.literal_eval(node.value)
    return result


def build_report(source, scan, identity=None):
    original = {r['code']: r for r in source['rows']}
    active = [t.removesuffix('.T') for t in scan['TICKERS']]
    if len(original) != len(source['rows']) or len(active) != len(set(active)):
        raise ValueError('Duplicate code: review universe before continuing')
    rows = []
    identities = {r['code']: r for r in (identity or {}).get('rows', [])}
    for code in sorted(set(original) | set(active)):
        item = original.get(code, {})
        verified_identity = identities.get(code, {})
        ticker = code + '.T'
        rows.append({
            'code': code, 'source_name': item.get('name'),
            'runtime_name': scan['STOCK_NAMES'].get(ticker),
            'in_original_selection': code in original,
            'in_runtime_universe': code in active,
            'selection_reason': '既存監視対象' if code in active else '現行対象外・除外理由未記録',
            'source_claim': item.get('source_claim'),
            'source_verified': item.get('source_verified') is True,
            'selection_acceptance': source.get('selection_acceptance', {}).get('method'),
            'accepted_on': source.get('selection_acceptance', {}).get('accepted_on'),
            'identity_status': verified_identity.get('status', 'unknown'),
            'official_name': verified_identity.get('official_name'),
            'identity_source_url': verified_identity.get('source_url'),
            'legacy_fund_score': scan['FUND_SCORES'].get(ticker),
            'fundamental_status': '未検証',
            'fundamental_evidence_url': None,
            'fundamental_as_of': None,
            'topix_status': '未照合',
            'topix_effective_date': None,
            'name_review_required': verified_identity.get('status') == 'unknown' or bool(
                not verified_identity and item and scan['STOCK_NAMES'].get(ticker)
                and item['name'] != scan['STOCK_NAMES'][ticker]),
        })
    return {'version': 1, 'purpose': '監視母集団の監査台帳。売買判定には未接続。固定業績点を検証済みと扱わない。',
            'source': source['source'],
            'accepted_on': source.get('selection_acceptance', {}).get('accepted_on'),
            'counts': {'original': len(original), 'runtime': len(active),
                       'original_not_runtime': len(set(original)-set(active)),
                       'runtime_not_original': len(set(active)-set(original)),
                       'legacy_scores_in_runtime': sum(c+'.T' in scan['FUND_SCORES'] for c in active)},
            'rows': rows}


if __name__ == '__main__':
    source = json.loads((ROOT/'audit/shikiho_candidates_2026.json').read_text())
    path = ROOT/'audit/security_identity.json'
    identity = json.loads(path.read_text()) if path.exists() else None
    report = build_report(source, assignments((ROOT/'scan.py').read_text()), identity)
    (ROOT/'audit/universe_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report['counts'], ensure_ascii=False))
