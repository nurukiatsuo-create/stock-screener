import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime
import pytz

# ============================================================
# 監視対象ユニバース（全80銘柄）
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

def analyze_market():
    nh_candidates = []
    soba_candidates = []
    
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = datetime.now(jst)
    updated_str = now_jst.strftime('%m/%d %H:%M')

    print(f">>> スクリーニング開始: {updated_str}")

    for ticker in TICKERS:
        try:
            t = yf.Ticker(ticker)
            df = t.history(period="1y")
            if len(df) < 60:
                continue

            # ----------------------------------------------------
            # 1. 財務データの取得（低PBR足切り ＆ 3大業績指標の採点）
            # ----------------------------------------------------
            info = t.info
            pbr = info.get("priceToBook", None)
            roe = info.get("returnOnEquity", None)
            rev_growth = info.get("revenueGrowth", None)
            earn_growth = info.get("earningsQuarterlyGrowth", None)

            # 【足切り①】低PBR（1.2倍未満）の放置株は排除
            if pbr is not None and pbr < 1.2:
                continue

            # 【業績スコア（50〜100点）】
            funda_score = 50
            if rev_growth is not None and rev_growth > 0.10:   # 売上二桁増（勝率41%指標）
                funda_score += 20
            if roe is not None and roe > 0.12:                 # 高ROE（PF 4.18指標）
                funda_score += 15
            if earn_growth is not None and earn_growth > 0.30: # 利益急増（モメンタム加速）
                funda_score += 15
            funda_score = min(funda_score, 100)

            # ----------------------------------------------------
            # 2. テクニカル指標の計算（売買代金足切り）
            # ----------------------------------------------------
            close = df['Close'].iloc[-1]
            open_p = df['Open'].iloc[-1]
            vol = df['Volume'].iloc[-1]
            
            # 【足切り②】板薄排除（直近5日平均売買代金 4,000万円以上）
            avg_turnover = (df['Close'].tail(5) * df['Volume'].tail(5)).mean()
            if avg_turnover < 40000000:
                continue

            sma5 = df['Close'].rolling(5).mean().iloc[-1]
            sma20 = df['Close'].rolling(20).mean().iloc[-1]
            sma50 = df['Close'].rolling(50).mean().iloc[-1]
            sma60 = df['Close'].rolling(60).mean().iloc[-1] if len(df) >= 60 else sma50
            vol20 = df['Volume'].rolling(20).mean().iloc[-1]

            # 過去250営業日の最高値（当日を除く）
            high250 = df['High'].iloc[:-1].tail(250).max()
            off_high = round(((close - high250) / high250) * 100, 1)

            # ----------------------------------------------------
            # 3. 新高値チャート採点（位置と出来高）
            # ----------------------------------------------------
            nh_score = 50
            if close > sma50:
                nh_score += 15
            if -3.0 <= off_high <= 2.5:   # 発射台ゾーン
                nh_score += 20
            elif -7.5 <= off_high < -3.0: # 助走ゾーン
                nh_score += 10
            elif off_high > 5.0:          # 飛びつき過熱
                nh_score -= 20

            if vol20 > 0 and vol >= vol20 * 1.3:
                nh_score += 15

            nh_score = min(max(nh_score, 0), 100)

            # ----------------------------------------------------
            # 4. 相場流パターンの判定
            # ----------------------------------------------------
            soba_score = 50
            soba_pattern = "通常"
            if (sma5 > sma20 > sma60):
                soba_score += 20
                soba_pattern = "PPP"

            if close > sma5 and open_p < sma5 and close > open_p:
                soba_score += 25
                soba_pattern = "★下半身(即買)"
            elif sma5 > sma20 and df['Close'].rolling(5).mean().iloc[-2] <= df['Close'].rolling(20).mean().iloc[-2]:
                soba_score += 25
                soba_pattern = "★くちばし(即買)"

            soba_score = min(max(soba_score, 0), 100)
            code_clean = ticker.replace(".T", "")
            
            # リスト格納（発射台圏内）
            if close > sma50 and -7.5 <= off_high <= 3.0:
                nh_candidates.append({
                    "code": code_clean,
                    "name": code_clean,
                    "price": int(close),
                    "nh_score": nh_score,        # チャート点
                    "funda_score": funda_score,  # 業績点
                    "off_high": off_high
                })

            if soba_score >= 70:
                soba_candidates.append({
                    "code": code_clean,
                    "name": code_clean,
                    "price": int(close),
                    "soba_score": soba_score,
                    "nh_score": nh_score,
                    "soba_pattern": soba_pattern
                })

        except Exception:
            continue

    # --------------------------------------------------------
    # 5. 並び替え（★バックテスト検証結果 PF 4.11 を最優先反映）
    # --------------------------------------------------------
    nh_candidates.sort(key=lambda x: (
        1 if (75 <= x['nh_score'] <= 90) else 0,   # ① 発射台スコア
        x['funda_score'],                           # ② 業績スコア（100点、85点...）
        1 if (-3.0 <= x['off_high'] < 0.0) else 0,  # ③ ★PF 4.11の「新高値直前」を最優先！
        x['nh_score'],                              # ④ チャート点
        -abs(x['off_high'])                         # ⑤ 高値の壁に近い順
    ), reverse=True)

    soba_candidates.sort(key=lambda x: x['soba_score'], reverse=True)

    output_data = {
        "updated_at": updated_str,
        "new_high_ranks": nh_candidates[:10],
        "soba_ranks": soba_candidates[:10]
    }

    with open("stocks_data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(">>> 完了: stocks_data.json を生成しました。")

if __name__ == "__main__":
    analyze_market()
