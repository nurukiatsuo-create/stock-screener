import json
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# ==========================================
# 四季報厳選ユニバース（全112銘柄）
# ==========================================
TICKERS = [
    # カテゴリ1: フィジカルAI・ロボティクス・自動化・電子部品 (28銘柄)
    "6652.T",
    "6862.T",
    "6855.T",
    "6407.T",
    "6134.T",
    "6629.T",
    "6226.T",
    "6904.T",
    "6368.T",
    "6727.T",
    "6941.T",
    "6946.T",
    "6866.T",
    "7254.T",
    "6258.T",
    "6518.T",
    "6345.T",
    "6616.T",
    "218A.T",
    "6677.T",
    "6474.T",
    "6327.T",
    "7715.T",
    "6508.T",
    "7218.T",
    "6286.T",
    "6364.T",
    "7256.T",
    # カテゴリ2: DX・クラウド・ソフトウェア・情報通信 (28銘柄)
    "4776.T",
    "3923.T",
    "6027.T",
    "3663.T",
    "3968.T",
    "155A.T",
    "5033.T",
    "4055.T",
    "5254.T",
    "9343.T",
    "4828.T",
    "4825.T",
    "4258.T",
    "3692.T",
    "3795.T",
    "4012.T",
    "3763.T",
    "7094.T",
    "3696.T",
    "3040.T",
    "3695.T",
    "4440.T",
    "4371.T",
    "4414.T",
    "4396.T",
    "4261.T",
    "5591.T",
    "135A.T",
    # カテゴリ3: 半導体・先端製造装置・高収益ニッチトップ (28銘柄)
    "6998.T",
    "6871.T",
    "7826.T",
    "6787.T",
    "4368.T",
    "4369.T",
    "4975.T",
    "4626.T",
    "4971.T",
    "4046.T",
    "5367.T",
    "3441.T",
    "5957.T",
    "1401.T",
    "3449.T",
    "4360.T",
    "6469.T",
    "4970.T",
    "6912.T",
    "5805.T",
    "7609.T",
    "4461.T",
    "7781.T",
    "5983.T",
    "5018.T",
    "6336.T",
    "4100.T",
    "4366.T",
    # カテゴリ4: 独自ビジネスモデル・高収益内需・インフラ・金融 (28銘柄)
    "7172.T",
    "3482.T",
    "2986.T",
    "3498.T",
    "9337.T",
    "4743.T",
    "7148.T",
    "2180.T",
    "2884.T",
    "1438.T",
    "9245.T",
    "5136.T",
    "6189.T",
    "7065.T",
    "3359.T",
    "7372.T",
    "7371.T",
    "5589.T",
    "4479.T",
    "156A.T",
    "7030.T",
    "3560.T",
    "9249.T",
    "7354.T",
    "7192.T",
    "7059.T",
    "4765.T",
    "7175.T",
]

# 主要銘柄の日本語名マッピング
NAME_MAP = {
    "6652.T": "IDEC",
    "4776.T": "サイボウズ",
    "7172.T": "JIA",
    "3763.T": "プロシップ",
    "3923.T": "ラクス",
    "6027.T": "弁護士コム",
    "6407.T": "CKD",
    "6134.T": "FUJI",
    "6941.T": "山一電機",
    "6871.T": "マイクロニクス",
    "4368.T": "扶桑化学",
    "3482.T": "ロードスター",
    "3498.T": "霞ヶ関キャピ",
    "7148.T": "FPG",
    "6998.T": "日本タングステン",
    "6862.T": "ミナトHD",
    "6855.T": "日本電子材料",
    "6368.T": "オルガノ",
    "6226.T": "守谷輸送機",
    "6904.T": "原田工業",
    "6727.T": "ワコム",
    "6946.T": "日本アビオ",
    "6866.T": "HIOKI",
    "6258.T": "平田機工",
    "6616.T": "トレックスセミ",
    "6677.T": "エスケーエレク",
    "6474.T": "不二越",
    "6327.T": "北川精機",
    "7715.T": "長野計器",
    "6508.T": "明電舎",
    "6364.T": "北越工業",
    "3663.T": "セルシス",
    "3968.T": "セグエグループ",
    "5033.T": "ヌーラボ",
    "4055.T": "ティアンドエス",
    "5254.T": "Arent",
    "9343.T": "アイビス",
    "4828.T": "ビジネスエンジ",
    "4825.T": "ウェザーニューズ",
    "4258.T": "網屋",
    "3692.T": "FFRI",
    "3795.T": "トヨクモ",
    "4012.T": "アクシス",
    "7094.T": "NexTone",
    "3696.T": "セレス",
    "3040.T": "ソリトン",
    "4371.T": "コアコンセプト",
    "4414.T": "フレクト",
    "4396.T": "システムサポート",
    "5591.T": "AVILEN",
    "7826.T": "フルヤ金属",
    "6787.T": "メイコー",
    "4369.T": "トリケミカル",
    "4975.T": "JCU",
    "4626.T": "太陽HD",
    "4971.T": "メック",
    "4046.T": "大阪ソーダ",
    "5367.T": "ニッカトー",
    "3441.T": "山王",
    "5957.T": "日東精工",
    "3449.T": "テクノフレックス",
    "6469.T": "放電精密",
    "4970.T": "東洋合成",
    "6912.T": "菊水HD",
    "5805.T": "SWCC",
    "7609.T": "ダイトロン",
    "4461.T": "第一工業製薬",
    "5018.T": "MORESCO",
    "6336.T": "石井表記",
    "4100.T": "戸田工業",
    "2986.T": "LAホールディングス",
    "9337.T": "トリドリ",
    "4743.T": "アイティフォー",
    "2180.T": "サニーサイド",
    "2884.T": "ヨシムラフード",
    "9245.T": "リベロ",
    "5136.T": "tripla",
    "6189.T": "グローバルキッズ",
    "7065.T": "ユーピーアール",
    "3359.T": "cotta",
    "7372.T": "デコルテHD",
    "7371.T": "Zenken",
    "5589.T": "オートサーバー",
    "4479.T": "マクアケ",
    "7030.T": "スプリックス",
    "3560.T": "ほぼ日",
    "9249.T": "日本エコシス",
    "7192.T": "日本モーゲージ",
    "7059.T": "コプロHD",
    "4765.T": "SBIグローバル",
    "7175.T": "今村証券",
}


def run_screening():
  print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 四季報厳選"
      f" {len(TICKERS)} 銘柄を取得中..."
  )

  data = yf.download(
      TICKERS,
      period="1y",
      interval="1d",
      group_by="ticker",
      auto_adjust=False,
      threads=True,
      progress=False,
  )

  candidates = []

  for code in TICKERS:
    try:
      df = data[code].dropna()
      if len(df) < 50:
        continue

      curr_close = float(df["Close"].iloc[-1])
      curr_vol = float(df["Volume"].iloc[-1])

      high_250 = float(df["High"].tail(250).max())
      off_high_pct = ((curr_close - high_250) / high_250) * 100

      vol_sma20 = float(df["Volume"].tail(20).mean())
      vol_ratio = (curr_vol / vol_sma20) if vol_sma20 > 0 else 1.0

      sma50 = float(df["Close"].tail(50).mean())
      sma200 = (
          float(df["Close"].tail(200).mean()) if len(df) >= 200 else sma50
      )

      # オニール新高値スコアリング
      score = 0
      if off_high_pct >= -3.0:
        score += 50
      elif off_high_pct >= -6.0:
        score += 40
      elif off_high_pct >= -10.0:
        score += 25
      elif off_high_pct >= -15.0:
        score += 10

      if vol_ratio >= 1.5:
        score += 30
      elif vol_ratio >= 1.2:
        score += 20
      elif vol_ratio >= 1.0:
        score += 10

      if curr_close > sma50:
        score += 10
      if curr_close > sma200:
        score += 10

      if off_high_pct >= -20.0 and curr_close > sma50:
        clean_code = code.replace(".T", "")
        name = NAME_MAP.get(code, f"銘柄{clean_code}")
        candidates.append({
            "ticker": code,
            "name": name,
            "price": int(curr_close),
            "breakout_score": score,
            "off_high_pct": round(off_high_pct, 1),
            "vol_ratio": round(vol_ratio, 2),
            "chart_url": (
                f"https://jp.tradingview.com/chart/?symbol=TSE%3A{clean_code}"
            ),
        })
    except Exception:
      continue

  candidates.sort(key=lambda x: x["breakout_score"], reverse=True)
  top30 = candidates[:30]

  output_data = {
      "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "count": len(top30),
      "ready": top30,
  }

  with open("watchlist.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

  print(
      f"スクリーニング完了: {len(top30)} 銘柄を watchlist.json に出力しました。"
  )


if __name__ == "__main__":
  run_screening()
