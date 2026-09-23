import os
import json
from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use('Agg') # サーバー用バックエンド
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 四季報2026年秋号 厳選26銘柄
TICKERS = [
    "3489.T", "3695.T", "3763.T", "3923.T", "4776.T",
    "5885.T", "6027.T", "6045.T", "6071.T", "6088.T",
    "6194.T", "6226.T", "6616.T", "6652.T", "6855.T",
    "6857.T", "6862.T", "6998.T", "7094.T", "7172.T",
    "7685.T", "7744.T", "7792.T", "7806.T", "8136.T",
    "9766.T"
]

os.makedirs("charts", exist_ok=True)
jst = pytz.timezone('Asia/Tokyo')
now_jst = datetime.now(jst).strftime('%m/%d %H:%M')

# 日経平均判定
n225 = yf.download("^N225", period="6mo", auto_adjust=True, progress=False)
if isinstance(n225.columns, pd.MultiIndex):
    n225.columns = n225.columns.get_level_values(0)
n225['SMA25'] = n225['Close'].rolling(25).mean()
market_ok = bool(n225['Close'].iloc[-1] >= n225['SMA25'].iloc[-1])

ready_list = []
forming_count = 0

for t in TICKERS:
    try:
        df = yf.download(t, period="1y", auto_adjust=True, progress=False)
        if len(df) < 60:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['SMA25'] = df['Close'].rolling(25).mean()
        df['SMA50'] = df['Close'].rolling(min(50, len(df))).mean()
        if len(df) >= 150:
            df['SMA200'] = df['Close'].rolling(min(200, len(df))).mean()
            trend_ok = (df['Close'].iloc[-1] > df['SMA50'].iloc[-1]) and (df['SMA50'].iloc[-1] > df['SMA200'].iloc[-1])
        else:
            trend_ok = df['Close'].iloc[-1] > df['SMA50'].iloc[-1]

        df['Vol20'] = df['Volume'].rolling(20).mean()
        turnover = df['Close'].iloc[-1] * df['Vol20'].iloc[-1]
        liquidity_ok = turnover >= 100_000_000

        close = float(df['Close'].iloc[-1])
        high_52w = float(df['High'].tail(min(250, len(df))).max())
        near_high = close >= (high_52w * 0.85)

        high_10d = float(df['High'].tail(10).max())
        low_10d = float(df['Low'].tail(10).min())
        range_10d = (high_10d - low_10d) / low_10d * 100

        pivot = round(high_10d, 1)
        max_buy = round(pivot * 1.05, 1)
        vol_target = int(df['Vol20'].iloc[-1] * 1.5)
        clean_ticker = t.replace(".T", "")

        if near_high and trend_ok and liquidity_ok:
            if range_10d <= 15.0:
                # --- CAN-SLIM チャート画像生成 ---
                plot_df = df.tail(100).copy()
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
                plt.subplots_adjust(hspace=0.08)

                # 上段：株価・各種ライン
                ax1.plot(plot_df.index, plot_df['Close'], label='株価', color='#111111', lw=1.5)
                ax1.plot(plot_df.index, plot_df['SMA25'], label='25日線', color='#007aff', lw=1.2, ls='--')
                ax1.plot(plot_df.index, plot_df['SMA50'], label='50日線', color='#34c759', lw=1.4)
                if 'SMA200' in df.columns and len(df) >= 200:
                    ax1.plot(plot_df.index, plot_df['SMA200'], label='200日線', color='#af52de', lw=1.4)

                ax1.axhline(high_52w, color='#ff3b30', ls=':', lw=1.5, label=f'52週高値 ({high_52w:,.0f}円)')
                ax1.axhline(pivot, color='#ff9500', lw=1.8, label=f'ピボット ({pivot:,.0f}円)')
                ax1.axhspan(pivot, max_buy, color='#ffcc00', alpha=0.25, label=f'適正買付エリア (+5%: 〜{max_buy:,.0f}円)')

                box_dates = plot_df.tail(10).index
                ax1.axvspan(box_dates[0], box_dates[-1], color='#5ac8fa', alpha=0.15, label=f'10日VCP収縮 ({range_10d:.1f}%)')

                ax1.set_title(f"【新高値・VCPブレイク検証】 {clean_ticker} (終値: {close:,.0f}円)", fontsize=13, fontweight='bold')
                ax1.grid(True, linestyle='--', alpha=0.4)
                ax1.legend(loc='upper left', fontsize=8, framealpha=0.9)

                # 下段：出来高・1.5倍ライン
                colors = ['#ff3b30' if c >= o else '#007aff' for c, o in zip(plot_df['Close'], plot_df['Open'])]
                ax2.bar(plot_df.index, plot_df['Volume'], color=colors, alpha=0.6, width=0.8)
                ax2.plot(plot_df.index, plot_df['Vol20'], color='#ff9500', lw=1.2, label='20日平均出来高')
                ax2.plot(plot_df.index, plot_df['Vol20'] * 1.5, color='#ff3b30', lw=1.2, ls='--', label=f'機関投資家シグナル (1.5倍: {vol_target:,}株)')
                ax2.grid(True, linestyle='--', alpha=0.4)
                ax2.legend(loc='upper left', fontsize=8, framealpha=0.9)
                ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))

                chart_path = f"charts/{clean_ticker}.png"
                plt.savefig(chart_path, dpi=130, bbox_inches='tight')
                plt.close()

                img_url = f"https://raw.githubusercontent.com/nurukiatsuo-create/stock-screener/main/charts/{clean_ticker}.png"

                ready_list.append({
                    "ticker": clean_ticker,
                    "close": int(close),
                    "pivot": int(pivot),
                    "max_buy": int(max_buy),
                    "vol_target": vol_target,
                    "range": f"{range_10d:.1f}%",
                    "chart_url": img_url
                })
            else:
                forming_count += 1
    except Exception as e:
        pass

output_data = {
    "updated_at": now_jst,
    "market_ok": market_ok,
    "ready": ready_list,
    "forming_count": forming_count
}

with open("watchlist.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)
