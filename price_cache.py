"""Reuse only valid observations from the SAME completed trading session."""
import copy


def restore_confirmed_cache(observations, snapshot, expected_date):
    result = copy.deepcopy(observations)
    for row in result.values():
        row['price_source'] = 'download' if row.get('evidence', {}).get('data_valid') else 'unavailable'
    restored = []
    if snapshot.get('data_date') != expected_date:
        return result, restored
    lookup = {}
    conflicts = set()
    for group in snapshot.get('breakout_board', {}).values():
        if not isinstance(group, list):
            continue
        for row in group:
            code = str(row['code'])
            if code in lookup and lookup[code] != row:
                conflicts.add(code)
            lookup[code] = row
    for code, previous in lookup.items():
        if code in conflicts:
            continue
        current = result.get(code, {}).get('evidence', {})
        if current.get('data_valid') and current.get('today', {}).get('date') == expected_date:
            continue
        e, box = previous.get('evidence', {}), previous.get('box_strategy', {})
        if not (e.get('data_valid') is True and e.get('today', {}).get('date') == expected_date
                and box.get('valid') is True and box.get('date') == expected_date):
            continue
        row = copy.deepcopy(previous)
        row.update(price_source='cached_confirmed',
                   price_fetch_status='再取得失敗・同じ取引日の保存済み日足を使用',
                   price_cached_updated_at=snapshot.get('updated_at'))
        result[code] = row
        restored.append(code)
    return result, sorted(restored)
