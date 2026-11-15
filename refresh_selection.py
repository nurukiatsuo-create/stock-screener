"""Reassess a stored price snapshot without pretending that prices were updated."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from candidate_gates import apply_selection, load_inputs


def refresh(root, as_of, now=None):
    root = Path(root)
    path = root/'stocks_data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    if not data.get('data_date') or data['data_date'] > as_of:
        raise ValueError('Invalid/future price snapshot date')
    config = json.loads((root/'trading_config.json').read_text())
    data['strategy'], report = apply_selection(data['strategy'], load_inputs(root), config, as_of, data['data_date'])
    data['screening_updated_at'] = (now or datetime.now(ZoneInfo('Asia/Tokyo'))).isoformat(timespec='seconds')
    data['screening_refresh_note'] = '保存済み日足に対する選別条件の再評価。株価の再取得・技術条件の再計算ではない。'
    data['fundamental_audit_summary'] = {k: v for k, v in report.items() if k != 'rows'}
    serialized = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    temp = path.with_suffix('.json.tmp')
    temp.write_text(serialized, encoding='utf-8'); temp.replace(path)
    (root/'audit/fundamental_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    return data['strategy']['selection_counts']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', required=True)
    args = parser.parse_args()
    print(json.dumps(refresh(Path(__file__).parent, args.as_of), ensure_ascii=False))
