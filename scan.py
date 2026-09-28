import json
from datetime import datetime

import pandas as pd
import pytz
import yfinance as yf

# ============================================================
# 監視ユニバース（現行scan.pyの80銘柄）
# ============================================================
TICKERS = [
    "7826.T", "6912.T", "9249.T", "7192.T", "6727.T", "6364.T", "3560.T", "5957.T",
    "7172.T", "1401.T", "6652.T", "6345.T", "6862.T", "6855.T", "6407.T", "6134.T",
    "6629.T", "6226.T", "6904.T", "6368.T", "6941.T", "6946.T", "6866.T", "7254.T",
    "6258.T", "6518.T", "6616.T", "6677.T", "6474.T", "6327.T", "7715.T", "6508.T",
    "4776.T", "3923.T", "6027.T", "3663.T", "3968.T", "5033.T", "4055.T", "5254.T",
    "4828.T", "4825.T", "4258.T", "3692.T", "4012.T", "3763.T", "7094.T", "3696.T",
    "3040.T", "4440.T", "4371.T", "4414.T", "4396.T", "5591.T", "6998.T", "6871.T",
    "6787.T", "4368.T", "4369.T", "4975.T", "4626.T", "4971.T", "4046.T", "3441.T",
    "3449.T", "4970.T", "5805.T", "7609.T", "4461.T", "7781.T", "5018.T", "4100.T",
    "3482.T", "3498.T", "7148.T", "2884.T", "5136.T", "7372.T", "5589.T", "4765.T"
]

# 52週高値と20日出来高平均を安定して計算するため2年分取得。
# 通常ランキングの判定式は、従来のscan.pyから変更していません。
HISTORY_PERIOD = "2y"
MIN_HISTORY_ROWS = 60
PF411_MIN_HISTORY_ROWS = 260
MIN_AVG_TURNOVER = 40_000_000


def matches_pf411_prebreakout(off_high, close, sma50, volume, vol20, history_rows):
    """PF4.11バックテストの新高値直前グループに対応する技術条件。"""
    return (
        history_rows >= PF411_MIN_HISTORY_ROWS
        and off_high is not None
        and pd.notna(off_high)
        and -3.0 <= off_high < 0.0
        and close > sma50
        and pd.notna(vol20)
        and vol20 > 0
        and volume >= vol20 * 1.2
    )


def analyze_market():
    nh_candidates = []
    soba_candidates = []
    pf411_candidates = []

    jst = pytz.timezone("Asia/Tokyo")
    now_jst = datetime.now(jst)
    updated_str = now_jst.strftime("%m/%d %H:%M")
    print(f">>> スクリーニング開始: {updated_str}")

    for ticker in TICKERS:
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=HISTORY_PERIOD)
            df = df.dropna(subset=["Open", "High", "Close", "Volume"]).copy()
            if len(df) < MIN_HISTORY_ROWS:
                print(f"データ不足でスキップ: {ticker} ({len(df)}行)")
                continue

            close = float(df["Close"].iloc[-1])
            open_p = float(df["Open"].iloc[-1])
            vol = float(df["Volume"].iloc[-1])

            sma5_series = df["Close"].rolling(5).mean()
            sma20_series = df["Close"].rolling(20).mean()
            sma50_series = df["Close"].rolling(50).mean()
            sma60_series = df["Close"].rolling(60).mean()
            vol20_series = df["Volume"].rolling(20).mean()
            high250_series = df["High"].rolling(250).max().shift(1)

            sma5 = float(sma5_series.iloc[-1])
            sma20 = float(sma20_series.iloc[-1])
            sma50 = float(sma50_series.iloc[-1])
            sma60 = float(sma60_series.iloc[-1])
            vol20 = float(vol20_series.iloc[-1])
            high250 = high250_series.iloc[-1]

            if pd.notna(high250) and float(high250) > 0:
                off_high = ((close - float(high250)) / float(high250)) * 100
            else:
                off_high = None
            vol_ratio = vol / vol20 if pd.notna(vol20) and vol20 > 0 else 0.0

            # ----------------------------------------------------
            # PF4.11の「新高値直前」比較群に対応する技術条件
            # バックテストの分岐: -3.0% <= entry_off_high < 0.0%
            # かつ close > SMA50、出来高 >= 20日平均×1.2
            # これは当日終値時点のシグナル候補で、実際の翌営業日寄値約定ではありません。
            # 当時のPF4.11バックテストにPBR・売買代金足切りはなかったため、
            # この候補リストにはその2条件を適用しません。
            # ----------------------------------------------------
