"""Causal daily-bar observations, not a prediction or a DUKE compliance score.

The caller supplies confirmed, consistently adjusted OHLCV and an expected date.
No fundamental score or unverified box threshold is used as a buy gate.
"""
import numpy as np
import pandas as pd


def analyze_breakout(df, expected_date=None, high_window=250, volume_window=20):
    result = {"version": 1, "status": "判定不能", "data_valid": False,
              "buy_signal": None, "duke_compliance": "未認定",
              "warnings": [], "events": []}
    required = ["Open", "High", "Low", "Close", "Volume"]
    if not set(required).issubset(df.columns) or len(df) < high_window + 1:
        result["warnings"].append("必要なOHLCVまたは履歴が不足")
        return result
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        result["warnings"].append("日付の重複・並び順異常")
        return result
    a = df[required].to_numpy(dtype=float)
    o, h, l, c, v = a.T
    if (not np.isfinite(a).all() or (a[:, :4] <= 0).any() or (v < 0).any()
            or (h < np.maximum(o, c)).any() or (l > np.minimum(o, c)).any()):
        result["warnings"].append("欠損・非数値・OHLC整合性異常")
        return result
    dates = [pd.Timestamp(x).strftime("%Y-%m-%d") for x in df.index]
    result.update(data_valid=True, signal_date=dates[-1], expected_date=expected_date,
                  freshness="未確認" if expected_date is None else
                  ("一致" if dates[-1] == expected_date else "日付不一致"))
    if expected_date is not None and dates[-1] != expected_date:
        result["warnings"].append("期待する最新日足の日付と不一致")
    if (v[-high_window:] == 0).any():
        result["warnings"].append("直近履歴に出来高ゼロあり")

    def bar(i):
        level = float(h[i-high_window:i].max())
        span = h[i] - l[i]
        avg_vol = float(v[i-volume_window:i].mean())
        return {"date": dates[i], "reference_high": level,
                "open": float(o[i]), "high": float(h[i]), "low": float(l[i]),
                "close": float(c[i]), "volume": float(v[i]),
                "intraday_break": bool(h[i] > level),
                "close_break": bool(c[i] > level),
                "close_vs_high_pct": float((c[i] / level - 1) * 100),
                "volume_ratio_prior20": float(v[i] / avg_vol) if avg_vol > 0 else None,
                "close_location": float((c[i]-l[i])/span) if span > 0 else None,
                "upper_wick_fraction": float((h[i]-max(o[i], c[i]))/span) if span > 0 else None,
                "daily_change_pct": float((c[i]/c[i-1]-1)*100),
                "high_to_close_pct": float((c[i]/h[i]-1)*100),
                "gap_pct": float((o[i]/c[i-1]-1)*100),
                "bullish_body": bool(c[i] > o[i])}

    current = bar(len(df)-1)
    result["today"] = current
    if current["close_break"]:
        result["status"] = "終値突破・当日"
    elif current["intraday_break"]:
        result["status"] = "日中突破・終値未維持"
    elif c[-1] == current["reference_high"]:
        result["status"] = "高値同値・未突破"
    else:
        result["status"] = "当日未突破"

    # Each event retains the hurdle that existed BEFORE that event. Subsequent
    # highs never overwrite its anchor. Failed events remain visible.
    events = []
    for i in range(high_window, len(df)):
        event = bar(i)
        if not event["close_break"]:
            continue
        anchor = event["reference_high"]
        after = c[i+1:]
        failures = np.flatnonzero(after < anchor)
        first_fail = i + 1 + int(failures[0]) if len(failures) else None
        maintained = 0
        for price in after:
            if price < anchor:
                break
            maintained += 1
        event.update(
            subsequent_bars=len(after), maintained_bars=maintained,
            first_close_below_date=dates[first_fail] if first_fail is not None else None,
            latest_vs_anchor_pct=float((c[-1]/anchor-1)*100),
            latest_above_anchor=bool(c[-1] >= anchor),
            intraday_retest_count=int(np.sum(l[i+1:] <= anchor)),
            outcome=("当日・継続未確認" if not len(after) else
                     "終値割れ後に回復" if first_fail is not None and c[-1] >= anchor else
                     "終値割れ" if first_fail is not None else "終値維持中"),
        )
        events.append(event)
    result["event_count"] = len(events)
    result["events"] = events[-10:]
    result["latest_event"] = events[-1] if events else None
    survivors = [e for e in events if e["subsequent_bars"] and e["first_close_below_date"] is None]
    result["prior_surviving_event"] = survivors[-1] if survivors else None
    # Coarse structural observations for inspection only, never certified boxes.
    result["range_windows"] = []
    for n in (20, 40, 60):
        if len(df) < n+1:
            continue
        hi, lo = float(h[-n-1:-1].max()), float(l[-n-1:-1].min())
        result["range_windows"].append({"bars": n, "upper": hi, "lower": lo,
                                        "width_pct": (hi-lo)/hi*100})
    widths = []
    for sl in (slice(-11, -6), slice(-6, -1)):
        hi, lo = float(h[sl].max()), float(l[sl].min())
        widths.append((hi-lo)/hi*100)
    result["prior_5bar_contraction_ratio"] = widths[1]/widths[0] if widths[0] else None
    result["warnings"].extend([
        "ボックスの自動認定・買い判定ではない",
        "維持本数は観測日足数。将来のダマシを否定しない",
        "四季報選定は利用者が実施。固定業績点は判定に不使用",
    ])
    return result


def build_evidence_board(observations):
    """Separate lists, no uncalibrated composite confidence or forced top two."""
    board = {"close_breaks": [], "intraday_rejections": [],
             "holding_prior_breaks": [], "failed_prior_breaks": [],
             "watching": [], "unavailable": []}
    for row in observations.values():
        e = row["evidence"]
        if not e["data_valid"] or e.get("freshness") != "一致":
            board["unavailable"].append(row)
            continue
        if e["status"] == "終値突破・当日":
            board["close_breaks"].append(row)
        elif e["status"] == "日中突破・終値未維持":
            board["intraday_rejections"].append(row)
        else:
            board["watching"].append(row)
        if e.get("prior_surviving_event"):
            board["holding_prior_breaks"].append(row)
        event = e.get("latest_event")
        if event and event["first_close_below_date"] is not None:
            board["failed_prior_breaks"].append(row)
    # Alphabetic code order deliberately carries no investment ranking.
    for rows in board.values():
        rows.sort(key=lambda r: r["code"])
    return board
