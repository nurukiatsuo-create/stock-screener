import json
from datetime import datetime
import pandas as pd
import pytz
import yfinance as yf

# 四季報2026年秋号 厳選26銘柄
TICKERS = [
    "3489.T",
    "3695.T",
    "3763.T",
    "3923.T",
    "4776.T",
    "5885.T",
    "6027.T",
    "6045.T",
    "6071.T",
    "6088.T",
    "6194.T",
    "6226.T",
    "6616.T",
    "6652.T",
    "6855.T",
    "6857.T",
    "6862.T",
    "6998.T",
    "7094.T",
    "7172.T",
    "7685.T",
    "7744.T",
    "7792.T",
    "7806.T",
    "8136.T",
    "9766.T",
]

jst = pytz.timezone("Asia/Tokyo")
now_jst = datetime.now(jst).strftime("%m/%d %H:%M")

n225 = yf.download("^N225", period="6mo", auto_adjust=True, progress=False)
if isinstance(n225.columns, pd.MultiIndex):
  n225.columns = n225.columns.get_level_values(0)
n225["SMA25"] = n225["Close"].rolling(25).mean()

market_ok = bool(n225["Close"].iloc[-1] >= n225["SMA25"].iloc[-1])

ready_list = []
forming_count = 0

for t in TICKERS:
  try:
    df = yf.download(t, period="1y", auto_adjust=True, progress=False)
    if len(df) < 60:
      continue
    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.get_level_values(0)

    df["SMA50"] = df["Close"].rolling(min(50, len(df))).mean()
    if len(df) >= 150:
      df["SMA200"] = df["Close"].rolling(min(200, len(df))).mean()
      trend_ok = (df["Close"].iloc[-1] > df["SMA50"].iloc[-1]) and (
          df["SMA50"].iloc[-1] > df["SMA200"].iloc[-1]
      )
    else:
      trend_ok = df["Close"].iloc[-1] > df["SMA50"].iloc[-1]

    df["Vol20"] = df["Volume"].rolling(20).mean()
    turnover = df["Close"].iloc[-1] * df["Vol20"].iloc[-1]
    liquidity_ok = turnover >= 100_000_000

    close = float(df["Close"].iloc[-1])
    high_52w = float(df["High"].tail(min(250, len(df))).max())
    near_high = close >= (high_52w * 0.85)

    high_10d = float(df["High"].tail(10).max())
    low_10d = float(df["Low"].tail(10).min())
    range_10d = (high_10d - low_10d) / low_10d * 100

    pivot = round(high_10d, 1)
    max_buy = round(pivot * 1.05, 1)
    vol_target = int(df["Vol20"].iloc[-1] * 1.5)

    if near_high and trend_ok and liquidity_ok:
      if range_10d <= 15.0:
        ready_list.append({
            "ticker": t.replace(".T", ""),
            "close": int(close),
            "pivot": int(pivot),
            "max_buy": int(max_buy),
            "vol_target": vol_target,
            "range": f"{range_10d:.1f}%",
        })
      else:
        forming_count += 1
  except Exception:
    pass

output_data = {
    "updated_at": now_jst,
    "market_ok": market_ok,
    "n225_close": int(n225["Close"].iloc[-1]),
    "n225_sma25": int(n225["SMA25"].iloc[-1]),
    "ready": ready_list,
    "forming_count": forming_count,
}

with open("watchlist.json", "w", encoding="utf-8") as f:
  json.dump(output_data, f, ensure_ascii=False, indent=2)
