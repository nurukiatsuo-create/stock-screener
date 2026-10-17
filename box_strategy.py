"""General rectangle monitoring. Causal, provisional engineering parameters.
Not a DUKE certification, profit forecast, or order execution engine.
"""
from dataclasses import dataclass, asdict
import math
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BoxConfig:
    min_bars: int = 20
    max_bars: int = 65
    max_width_pct: float = 15.0
    touch_fraction: float = 0.15  # outer 15% of box height
    pivot_radius: int = 2        # pivot becomes known two bars later
    min_touch_gap: int = 5


def detect_box(df, cfg=BoxConfig()):
    """Use only supplied completed bars; two distinct reactions on each side."""
    if len(df) < cfg.min_bars or (df.High.tail(cfg.max_bars).nunique() < 2 and df.Low.tail(cfg.max_bars).nunique() < 2):
        return None
    for n in range(min(len(df), cfg.max_bars), cfg.min_bars-1, -1):
        w = df.iloc[-n:]
        h, l = w.High.to_numpy(), w.Low.to_numpy()
        upper, lower = float(max(h)), float(min(l))
        width = upper-lower
        if width <= 0 or width/upper*100 > cfg.max_width_pct:
            continue
        touches = []
        for a, side in ((h, 'upper'), (l, 'lower')):
            points = []
            for j in range(cfg.pivot_radius, n-cfg.pivot_radius):
                neighbors = a[j-cfg.pivot_radius:j+cfg.pivot_radius+1]
                reaction = (a[j] == max(neighbors) and min(neighbors) < a[j]) if side == 'upper' else (a[j] == min(neighbors) and max(neighbors) > a[j])
                near = a[j] >= upper-width*cfg.touch_fraction if side == 'upper' else a[j] <= lower+width*cfg.touch_fraction
                if reaction and near and (not points or j-points[-1] >= cfg.min_touch_gap):
                    points.append(j)
            touches.append(points)
        if min(map(len, touches)) < 2:
            continue
        # Require alternating reactions, not two unrelated high/low clusters.
        order = sorted([(j, 'U') for j in touches[0]]+[(j, 'L') for j in touches[1]])
        alternations = sum(order[k][1] != order[k-1][1] for k in range(1,len(order)))
        if alternations < 3:
            continue
        return dict(upper=upper, lower=lower, bars=n, width_pct=width/upper*100,
                    start_date=str(w.index[0].date()), end_date=str(w.index[-1].date()),
                    upper_touches=len(touches[0]), lower_touches=len(touches[1]))
    return None


def analyze_boxes(df, cfg=BoxConfig()):
    required = ['Open','High','Low','Close','Volume']
    out = dict(valid=False, status='判定不能', parameters=asdict(cfg), boxes=[], events=[])
    if not set(required).issubset(df.columns) or len(df) < cfg.min_bars+1:
        return out
    try:
        a = df[required].to_numpy(dtype=float)
    except (ValueError, TypeError):
        return out
    if (not df.index.is_monotonic_increasing or df.index.has_duplicates or
        not np.isfinite(a).all() or (a[:,:4] <= 0).any() or (a[:,4] < 0).any() or
        (a[:,1] < np.maximum(a[:,0],a[:,3])).any() or (a[:,2] > np.minimum(a[:,0],a[:,3])).any()):
        return out
    active, search_start, breakout_index = None, 0, None
    state = '形成中'
    for i in range(cfg.min_bars, len(df)):
        date = str(df.index[i].date())
        # Recognition as of yesterday; boundary never incorporates today's bar.
        if active is None:
            found = detect_box(df.iloc[search_start:i], cfg)
            if found:
                active = dict(found, id=len(out['boxes'])+1, confirmed_date=date,
                              breakout_date=None, breakdown_date=None, stage=1)
                out['boxes'].append(active)
        elif breakout_index is not None:
            found = detect_box(df.iloc[breakout_index+1:i], cfg)
            if found and found['lower'] > active['lower'] and found['upper'] > active['upper']:
                active = dict(found, id=len(out['boxes'])+1, confirmed_date=date,
                              breakout_date=None, breakdown_date=None, stage=active["stage"]+1)
                out['boxes'].append(active)
                breakout_index = None
        row = df.iloc[i]
        state = '形成中'
        if active:
            if row.Close < active['lower']:
                state = '下抜け確認'
                active['breakdown_date'] = date
                out['events'].append(dict(date=date, kind=state, box_id=active['id'], lower=active['lower']))
                active, breakout_index, search_start = None, None, i+1
            elif row.Close > active['upper'] and active['breakout_date'] is None:
                state = '再上抜け' if active['stage'] > 1 else '終値上抜け'
                active['breakout_date'], breakout_index = date, i
                out['events'].append(dict(date=date, kind=state, box_id=active['id'], upper=active['upper']))
            elif row.Low < active['lower']:
                state = '日中下限割れ・終値回復'
            elif active['breakout_date']:
                state = '上抜け後・新ボックス形成中' if row.Close >= active['upper'] else '元ボックス内へ戻る'
            elif row.High > active['upper']:
                state = '日中上抜け・終値未維持'
            else:
                state = '新ボックス維持' if active['stage'] > 1 else 'ボックス内'
        if active and active['breakout_date'] and row.Close <= active['upper'] and not active.get('return_date'):
            active['return_date'] = date
    if active and breakout_index is not None:
        active['bars_since_breakout'] = len(df)-1-breakout_index
    out.update(valid=True, status=state, active_box=active, date=str(df.index[-1].date()))
    return out


def position_status(position, df, boxes):
    """User-confirmed purchase and initial box required; never import sample holdings."""
    try:
        price, shares = float(position['buy_price']), int(position['shares'])
        bought = str(position['buy_date'])
        lower, upper = float(position['box_lower']), float(position['box_upper'])
        if not all(math.isfinite(x) for x in (price,lower,upper)) or not 0 < lower < upper or price <= 0 or shares <= 0 or shares % 100:
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        return dict(status='保有設定不足・判定保留')
    if not boxes['valid'] or bought > boxes['date'] or bought < str(df.index[0].date()):
        return dict(status='履歴不足・判定保留')
    stop, exit_event = price*.9, None
    updates = {b['confirmed_date']: b for b in boxes['boxes'] if b['confirmed_date'] > bought}
    # Entry day's intraday low may precede the fill. Do not infer a stop fill.
    for dt,row in df.iterrows():
        d = str(dt.date())
        if d < bought:
            continue
        b = updates.get(d)
        if b and b['lower'] > lower and b['upper'] > upper:
            lower, upper = b['lower'], b['upper']
        if (d > bought and row.Low <= stop) or row.Close <= stop:
            exit_event = dict(date=d, reason='−10％損切り水準到達・約定要確認')
            break
        if row.Close < lower:
            exit_event = dict(date=d, reason='終値ボックス下限割れ・全売却シグナル')
            break
    close = float(df.Close.iloc[-1])
    return dict(status=exit_event['reason'] if exit_event else '保有継続', exit_event=exit_event,
                buy_price=price, shares=shares, cost=price*shares, close=close,
                pnl_yen=(close-price)*shares, pnl_pct=(close/price-1)*100,
                stop_price=stop, planned_loss_yen=price*shares*.1,
                management_lower=lower, management_upper=upper,
                add_candidate=not exit_event and close > price and boxes['status']=='再上抜け',
                note='注文機能なし。日足の到達は実際の約定を示さない。購入日の安値は判定対象外。')


ENTRY_DEFAULTS = dict(max_entry_bars=3, max_extension_pct=3.0,
                      min_volume_ratio=1.5, near_break_pct=5.0)


def entry_policy(config):
    policy = {**ENTRY_DEFAULTS, **config.get('entry_policy', {})}
    if set(policy) != set(ENTRY_DEFAULTS):
        raise ValueError('unknown entry_policy key')
    for key, value in policy.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('entry_policy values must be finite and positive')
    if not isinstance(policy['max_entry_bars'], int):
        raise ValueError('max_entry_bars must be an integer')
    return policy


def classify_entry(evidence, boxes, policy):
    """Technical screen only. First event per box; age never resets on new highs."""
    t, box = evidence['today'], boxes.get('active_box')
    result = dict(candidate=False, entry_group='other', entry_reasons=[])
    if not box or box.get('breakdown_date'):
        return dict(result, status=boxes['status'])
    close = t['close']
    upper, lower = box['upper'], box['lower']
    if not all(isinstance(x, (int, float)) and math.isfinite(x) and x > 0
               for x in (close, upper, lower, t['reference_high'])) or lower >= upper:
        return dict(result, status='データ確認待ち')
    extension = (close/upper-1)*100
    remaining = max(0, (max(upper, t['reference_high'])/close-1)*100)
    result.update(close_vs_box_upper_pct=extension, remaining_pct=remaining)
    if not box.get('breakout_date'):
        near = lower <= close <= upper and remaining <= policy['near_break_pct']
        return dict(result, entry_group='pre_break' if near else 'other',
                    status='突破直前・未突破' if near else boxes['status'])
    age = box.get('bars_since_breakout')
    if box['breakout_date'] > t['date'] or type(age) is not int or age < 0:
        return dict(result, status='データ確認待ち')
    result['entry_group'] = 'post_break'
    if box.get('return_date') or close <= upper:
        return dict(result, status='突破後に箱へ戻る・再形成待ち', entry_reasons=['箱突破の失敗履歴'])
    # The first closing new-high event after this box break is the fixed anchor.
    events = sorted((x for x in evidence.get('events', [])
                     if box['breakout_date'] <= x['date'] <= t['date']), key=lambda x:x['date'])
    event = events[0] if events else None
    reasons = []
    retained = evidence.get('events', [])
    if (evidence.get('event_count', len(retained)) > len(retained)
            and retained and box['breakout_date'] < retained[0]['date']):
        reasons.append('初回新高値の履歴不足')
    if age >= policy['max_entry_bars']:
        reasons.append('箱突破からの初動期間を超過')
    if extension > policy['max_extension_pct'] + 1e-9:
        reasons.append('箱上限からの乖離超過')
    if event is None:
        reasons.append('新高値未更新')
    else:
        result['entry_event'] = event
        if event.get('first_close_below_date') or close <= event['reference_high']:
            reasons.append('初回新高値の突破水準を維持できず')
        ratio = event.get('volume_ratio_prior20')
        if ratio is None or not math.isfinite(ratio) or ratio < policy['min_volume_ratio']:
            reasons.append('初回新高値突破の出来高不足')
    result['entry_reasons'] = reasons
    if not reasons:
        return dict(result, candidate=True, entry_group='initial_break', status='初動の技術条件該当')
    if extension > policy['max_extension_pct'] + 1e-9 or age >= policy['max_entry_bars']:
        return dict(result, status='初動対象外・新ボックス待ち')
    return dict(result, status='ボックス突破・新高値未更新' if event is None else '初動条件不足・監視継続')


def build_strategy(observations, config):
    policy = entry_policy(config)
    budget = float(config.get('budget_yen', 1000000))
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError('budget_yen must be positive')
    positions = config.get('positions', [])
    committed = sum(float(p['buy_price'])*int(p['shares']) for p in positions)
    available = max(0, budget-committed)
    sectors = config.get('sectors', {})
    held_sectors = {sectors.get(str(p['code'])) for p in positions}
    rows, candidates = [], []
    for code, r in observations.items():
        e, b = r['evidence'], r.get('box_strategy', {})
        row = dict(code=code, name=r['name'], box=b, sector=sectors.get(code), candidate=False)
        if (not e.get('data_valid') or e.get('freshness') != '一致' or not b.get('valid')
                or b.get('date') != e.get('today', {}).get('date')):
            row['status']='データ確認待ち'
        else:
            t, box = e['today'], b.get('active_box')
            row.update(close=t['close'], daily_change_pct=t['daily_change_pct'],
                       volume_ratio=t['volume_ratio_prior20'], upper_wick_fraction=t['upper_wick_fraction'],
                       close_location=t['close_location'], high_to_close_pct=t['high_to_close_pct'])
            row.update(classify_entry(e, b, policy))
            row['fundamental_check'] = '四季報選定済み・直近業績とビッグチェンジは要確認'
            row['buy_signal'] = None
            row['volume_label'] = '平均より増加' if row['volume_ratio'] is not None and row['volume_ratio'] > 1 else '増加の裏付けなし'
            row['close_vs_box_upper_pct'] = (t['close']/box['upper']-1)*100 if box else None
            max_shares = int(available//(t['close']*100))*100
            row['budget_preview'] = dict(max_shares=max_shares, cost=max_shares*t['close'],
                stop_price=t['close']*.9, planned_loss_yen=max_shares*t['close']*.1,
                basis='終値での予算上限試算。推奨株数・翌日約定価格ではない')
            row['sector_check'] = ('未確認' if not row['sector'] or (positions and None in held_sectors) else '重複あり' if row['sector'] in held_sectors else '登録済み保有との重複なし')
        rows.append(row)
        if row['candidate']:
            candidates.append(row)
    return dict(version=3, entry_policy=policy, candidates=sorted(candidates,key=lambda x:x['code']), observations=sorted(rows,key=lambda x:x['code']),
                budget_yen=budget, committed_yen=committed, available_yen=available,
                portfolio_warning='予算超過' if committed > budget else '基本1〜2銘柄。追加は手動確認',
                position_count=len(positions), auto_orders=False,
                policy='DUKE公開資料を参考にした技術条件の監視。数値閾値は独自設定。業績・事業変化の確認は別途必要。売買指示ではない。',
                freshness_note='銘柄間日付比較のみ。データ日を必ず確認。')
