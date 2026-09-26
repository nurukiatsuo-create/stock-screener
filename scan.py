import os
import json
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 監視ユニバース（四季報厳選銘柄群）
TICKERS = [
    "6652.T", "6862.T", "6855.T", "6407.T", "6134.T", "6629.T", "6226.T", "6904.T",
    "6368.T", "6727.T", "6941.T", "6946.T", "6866.T", "7254.T", "6258.T", "6518.T",
    "6345.T", "6616.T", "218A.T", "6677.T", "6474.T", "6327.T", "7715.T", "6508.T",
    "7218.T", "6286.T", "6364.T", "7256.T", "4776.T", "3923.T", "6027.T", "3663.T",
    "3968.T", "155A.T", "5033.T", "4055.T", "5254.T", "9343.T", "4828.T", "4825.T",
    "4258.T", "3692.T", "4012.T", "3763.T", "7094.T", "3696.T", "3040.T", "3695.T",
    "4440.T", "4371.T", "4414.T", "4396.T", "4261.T", "5591.T", "135A.T", "6998.T",
    "6871.T", "7826.T", "6787.T", "4368.T", "4369.T", "4975.T", "4626.T", "4971.T",
    "4046.T", "5367.T", "3441.T", "5957.T", "1401.T", "3449.T", "4360.T", "6469.T",
    "4970.T", "6912.T", "5805.T", "7609.T", "4461.T", "7781.T", "5983.T", "5018.T",
    "6336.T", "4100.T", "4366.T", "7172.T", "3482.T", "2986.T", "3498.T", "9337.T",
    "4743.T", "7148.T", "2180.T", "2884.T", "1438.T", "9245.T", "5136.T", "6189.T",
    "7065.T", "3359.T", "7372.T", "7371.T", "5589.T", "4479.T", "156A.T", "7030.T",
    "3560.T", "9249.T", "7354.T", "7192.T", "7059.T", "4765.T", "7175.T"
]

# 保有銘柄情報
HOLDINGS = {
    "6652.T": {"name": "IDEC", "buy_price": 3850, "note": "買3850 損切-7%: 3580円"},
    "6345.T": {"name": "アイチコーポ", "buy_price": 1474, "note": "買1474 損切-7%: 1370円"},
    "1401.T": {"name": "エムビーエス", "buy_price": 1420, "note": "買1420 建値逆指値でガチホ"}
}

# 銘柄名マッピング
TICKER_NAMES = {
    "6652.T": "IDEC", "6345.T": "アイチコーポ", "1401.T": "エムビーエス",
    "7172.T": "JIA", "5957.T": "日東精工", "6364.T": "北越工業", "7148.T": "FPG"
}

def calc_new_high_score(df):
    """5点刻みの新高値最適化採点ロジック（75〜90点が黄金エントリー）"""
    c = df["Close"].iloc[-1]
    h250 = df["High"].iloc[-250:-1].max()
    vol = df["Volume"].iloc[-1]
    vol_sma20 = df["Volume"].iloc[-21:-1].mean()
    sma50 = df["Close"].iloc[-50:].mean()
    sma200 = df["Close"].iloc[-200:].mean() if len(df) >= 200 else sma50

    off_high = ((c - h250) / h250) * 100 if h250 > 0 else -99
    vol_ratio = (vol / vol_sma20) if vol_sma20 > 0 else 1.0

    # 1. 高値乖離（最大50点）
    p_score = 0
    if off_high >= 0:      p_score = 50
    elif off_high >= -1.5: p_score = 45
    elif off_high >= -3.0: p_score = 40
    elif off_high >= -4.5: p_score = 35
    elif off_high >= -6.0: p_score = 30
    elif off_high >= -8.0: p_score = 25
    elif off_high >= -10.0:p_score = 20
    else:                  p_score = 10

    # 2. 出来高（最大30点）
    v_score = 0
    if vol_ratio >= 2.0:   v_score = 30
    elif vol_ratio >= 1.6: v_score = 25
    elif vol_ratio >= 1.4: v_score = 20
    elif vol_ratio >= 1.2: v_score = 15
    elif vol_ratio >= 1.0: v_score = 10
    else:                  v_score = 5

    # 3. トレンド（最大20点）
    t_score = 0
    if c > sma50:  t_score += 10
    if c > sma200: t_score += 10

    score = p_score + v_score + t_score

    # アクション判定
    if 75 <= score <= 90 and c > sma50:
        action = "★最優先発射台"
    elif score >= 95:
        action = "飛びつき見送り"
    elif score >= 65:
        action = "助走圏内"
    else:
        action = "押し目形成"

    return score, off_high, vol_ratio, action

def calc_soba_pattern(df):
    """相場流シグナル採点ロジック"""
    c = df["Close"].iloc[-1]
    sma5 = df["Close"].rolling(5).mean().iloc[-1]
    sma20 = df["Close"].rolling(20).mean().iloc[-1]
    sma60 = df["Close"].rolling(60).mean().iloc[-1] if len(df) >= 60 else sma20
    prev_c = df["Close"].iloc[-2]
    prev_sma5 = df["Close"].rolling(5).mean().iloc[-2]

    score = 50
    pattern = "調整中"

    # PPP（パンパカパーン：5 > 20 > 60）
    if sma5 > sma20 > sma60:
        score += 20
        pattern = "PPP継続"

    # 下半身（5日線の上抜け陽線）
    if prev_c < prev_sma5 and c > sma5 and (c > df["Open"].iloc[-1]):
        score += 30
        pattern = "★下半身(即買)"
    
    # くちばし（5日線が20日線を下から上抜く）
    elif prev_sma5 < sma20 and sma5 >= sma20:
        score += 25
        pattern = "★くちばし(即買)"

    return min(score, 100), pattern

# データ取得
print("最新株価データを取得中...")
df_all = yf.download(TICKERS, period="1y", interval="1d", group_by="ticker", auto_adjust=False, progress=False)

portfolio_list = []
new_high_list = []
soba_list = []

for code in TICKERS:
    try:
        if code not in df_all.columns.levels[0]: continue
        df = df_all[code].dropna().copy()
        if len(df) < 60: continue

        c = float(df["Close"].iloc[-1])
        name = TICKER_NAMES.get(code, code.replace(".T", ""))
        nh_score, off_h, v_ratio, nh_action = calc_new_high_score(df)
        soba_score, soba_pattern = calc_soba_pattern(df)

        item = {
            "code": code,
            "name": name,
            "price": round(c, 1),
            "nh_score": nh_score,
            "off_high": round(off_h, 1),
            "vol_ratio": round(v_ratio, 2),
            "nh_action": nh_action,
            "soba_score": soba_score,
            "soba_pattern": soba_pattern
        }

        # 保有銘柄チェック
        if code in HOLDINGS:
            h_info = HOLDINGS[code]
            buy_p = h_info["buy_price"]
            pnl = ((c - buy_p) / buy_p) * 100
            item["buy_price"] = buy_p
            item["pnl_pct"] = round(pnl, 2)
            item["note"] = h_info["note"]
            portfolio_list.append(item)

        new_high_list.append(item)
        soba_list.append(item)

    except Exception:
        continue

# ソート処理
# 新高値：75〜90点（最優先発射台）を一番上に配置し、スコア降順
def nh_sort_key(x):
    s = x["nh_score"]
    priority = 1 if (75 <= s <= 90) else (2 if s >= 95 else 3)
    return (priority, -s)

new_high_sorted = sorted(new_high_list, key=nh_sort_key)[:10]

# 相場流：相場スコア降順
soba_sorted = sorted(soba_list, key=lambda x: -x["soba_score"])[:10]

output_json = {
    "updated_at": pd.Timestamp.now().strftime("%m/%d %H:%M"),
    "portfolio": portfolio_list,
    "new_high_ranks": new_high_sorted,
    "soba_ranks": soba_sorted
}

# 保存
SAVE_FILE = "stocks_data.json"
with open(SAVE_FILE, "w", encoding="utf-8") as f:
    json.dump(output_json, f, ensure_ascii=False, indent=2)

print(f"出力完了: {SAVE_FILE}")
