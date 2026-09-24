import json
from datetime import datetime
import numpy as np
import pandas as pd
import yfinance as yf

# ==========================================
# 1. 四季報厳選ユニバース（全112銘柄）
# ==========================================
TICKERS = [
    # カテゴリ1: 自動化・ロボティクス・電子部品
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
    # カテゴリ2: DX・クラウド・ソフトウェア
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
    # カテゴリ3: 半導体・先端装置・ニッチトップ
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
    # カテゴリ4: 独自モデル・高収益内需・金融
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

# 保有ポジション設定
MY_POSITIONS = {"6652.T": {"buy_price": 3850, "shares": 100}}

# 全112銘柄 正式名称マッピング
NAME_MAP = {
    "6652.T": "IDEC",
    "6862.T": "ミナトHD",
    "6855.T": "日本電子材料",
    "6407.T": "CKD",
    "6134.T": "FUJI",
    "6629.T": "テクノホライゾン",
    "6226.T": "守谷輸送機",
    "6904.T": "原田工業",
    "6368.T": "オルガノ",
    "6727.T": "ワコム",
    "6941.T": "山一電機",
    "6946.T": "日本アビオ",
    "6866.T": "HIOKI",
    "7254.T": "ユニバンス",
    "6258.T": "平田機工",
    "6518.T": "三相電機",
    "6345.T": "アイチコーポ",
    "6616.T": "トレックスセミ",
    "218A.T": "Liberaware",
    "6677.T": "エスケーエレク",
    "6474.T": "不二越",
    "6327.T": "北川精機",
    "7715.T": "長野計器",
    "6508.T": "明電舎",
    "7218.T": "田中精密",
    "6286.T": "静甲",
    "6364.T": "北越工業",
    "7256.T": "河西工業",
    "4776.T": "サイボウズ",
    "3923.T": "ラクス",
    "6027.T": "弁護士コム",
    "3663.T": "セルシス",
    "3968.T": "セグエグループ",
    "155A.T": "情報戦略テク",
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
    "3763.T": "プロシップ",
    "7094.T": "NexTone",
    "3696.T": "セレス",
    "3040.T": "ソリトン",
    "3695.T": "GMOプロダクト",
    "4440.T": "ヴィッツ",
    "4371.T": "コアコンセプト",
    "4414.T": "フレクト",
    "4396.T": "システムサポート",
    "4261.T": "アジアクエスト",
    "5591.T": "AVILEN",
    "135A.T": "VRAIN",
    "6998.T": "日本タングステン",
    "6871.T": "マイクロニクス",
    "7826.T": "フルヤ金属",
    "6787.T": "メイコー",
    "4368.T": "扶桑化学",
    "4369.T": "トリケミカル",
    "4975.T": "JCU",
    "4626.T": "太陽HD",
    "4971.T": "メック",
    "4046.T": "大阪ソーダ",
    "5367.T": "ニッカトー",
    "3441.T": "山王",
    "5957.T": "日東精工",
    "1401.T": "エムビーエス",
    "3449.T": "テクノフレックス",
    "4360.T": "マナックケミカル",
    "6469.T": "放電精密",
    "4970.T": "東洋合成",
    "6912.T": "菊水HD",
    "5805.T": "SWCC",
    "7609.T": "ダイトロン",
    "4461.T": "第一工業製薬",
    "7781.T": "平山HD",
    "5983.T": "イワブチ",
    "5018.T": "MORESCO",
    "6336.T": "石井表記",
    "4100.T": "戸田工業",
    "4366.T": "ダイトーケミ",
    "7172.T": "JIA",
    "3482.T": "ロードスター",
    "2986.T": "LAホールディングス",
    "3498.T": "霞ヶ関キャピ",
    "9337.T": "トリドリ",
    "4743.T": "アイティフォー",
    "7148.T": "FPG",
    "2180.T": "サニーサイド",
    "2884.T": "ヨシムラフード",
    "1438.T": "岐阜造園",
    "9245.T": "リベロ",
    "5136.T": "tripla",
    "6189.T": "グローバルキッズ",
    "7065.T": "ユーピーアール",
    "3359.T": "cotta",
    "7372.T": "デコルテHD",
    "7371.T": "Zenken",
    "5589.T": "オートサーバー",
    "4479.T": "マクアケ",
    "156A.T": "マテリアルG",
    "7030.T": "スプリックス",
    "3560.T": "ほぼ日",
    "9249.T": "日本エコシス",
    "7354.T": "DmMiX",
    "7192.T": "日本モーゲージ",
    "7059.T": "コプロHD",
    "4765.T": "SBIグローバル",
    "7175.T": "今村証券",
}


def run_screening():
  print(
      f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 112銘柄の一括データ取得＆トータルW判定中..."
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

  stock_results = []

  for code in TICKERS:
    try:
      df = data[code].dropna()
      if len(df) < 25:
        continue

      curr_close = float(df["Close"].iloc[-1])
      prev_close = float(df["Close"].iloc[-2])
      curr_open = float(df["Open"].iloc[-1])
      curr_high = float(df["High"].iloc[-1])
      curr_low = float(df["Low"].iloc[-1])
      curr_vol = float(df["Volume"].iloc[-1])

      if curr_close > 1000000 or curr_close <= 0:
        continue

      # 移動平均線
      sma5 = df["Close"].rolling(5).mean()
      sma20 = df["Close"].rolling(20).mean()
      sma50 = df["Close"].rolling(50).mean()
      sma200 = df["Close"].rolling(200).mean()

      m5_val = float(sma5.iloc[-1])
      p_m5 = float(sma5.iloc[-2])
      m20_val = float(sma20.iloc[-1])
      p_m20 = float(sma20.iloc[-2])
      m20_3days = (
          float(sma20.iloc[-4]) if len(df) >= 4 else float(sma20.iloc[0])
      )

      # 1. オニール新高値スコア
      high_250 = float(df["High"].tail(250).max())
      off_high_pct = ((curr_close - high_250) / high_250) * 100
      vol_sma20 = float(df["Volume"].tail(20).mean())
      vol_ratio = (curr_vol / vol_sma20) if vol_sma20 > 0 else 1.0

      breakout_score = 0
      if off_high_pct >= -3.0:
        breakout_score += 50
      elif off_high_pct >= -6.0:
        breakout_score += 40
      elif off_high_pct >= -10.0:
        breakout_score += 25
      elif off_high_pct >= -15.0:
        breakout_score += 10

      if vol_ratio >= 1.5:
        breakout_score += 30
      elif vol_ratio >= 1.2:
        breakout_score += 20
      elif vol_ratio >= 1.0:
        breakout_score += 10

      sma50_val = float(sma50.iloc[-1]) if not np.isnan(sma50.iloc[-1]) else 0
      sma200_val = (
          float(sma200.iloc[-1])
          if not np.isnan(sma200.iloc[-1])
          else sma50_val
      )
      if curr_close > sma50_val:
        breakout_score += 10
      if curr_close > sma200_val:
        breakout_score += 10

      # 2. 相場流スコア ＆ 技判定
      is_yang = curr_close >= curr_open
      is_yin = curr_close < curr_open
      body_mid = (curr_open + curr_close) / 2
      ma20_slope = m20_val - m20_3days
      bias_20 = ((curr_close - m20_val) / m20_val) * 100

      hl = curr_high - curr_low
      body_size = abs(curr_close - curr_open)
      body_ratio = (body_size / hl) if hl > 0 else 0

      prev_diff = abs(p_m5 - p_m20)
      curr_diff = abs(m5_val - m20_val)
      is_kuchibashi = (p_m5 <= p_m20) and (m5_val > m20_val)
      is_mono = (
          (m5_val > m20_val)
          and (curr_diff > prev_diff)
          and (p_m5 - p_m20 < curr_close * 0.015)
      )
      is_dense = (abs(m5_val - m20_val) / curr_close) < 0.012

      is_kahanshin = (
          (prev_close <= p_m5)
          and (body_mid > m5_val)
          and (curr_close > m5_val)
          and is_yang
      )
      is_gyaku_kahanshin = (
          (curr_close < m5_val) and (body_mid < m5_val) and is_yin
      )
      is_ppp = (curr_close > m5_val) and (m5_val > m20_val)

      is_holding = code in MY_POSITIONS
      name = NAME_MAP.get(code, code.replace(".T", ""))
      clean_code = code.replace(".T", "")
      chart_url = f"https://jp.tradingview.com/chart/?symbol=TSE%3A{clean_code}"

      # 保有株（IDEC等）のエグジット判定
      if is_holding:
        buy_price = MY_POSITIONS[code]["buy_price"]
        stop_price = buy_price * 0.93

        if curr_close <= stop_price:
          status = "損切(-7%)"
          signal = "STOP"
        elif is_gyaku_kahanshin:
          status = "即手仕舞"
          signal = "EXIT"
        elif curr_close < m20_val:
          status = "20線割手仕舞"
          signal = "EXIT"
        elif curr_close < m5_val:
          status = "5線割警戒"
          signal = "CAUTION"
        elif is_ppp:
          status = "PPP継続"
          signal = "HOLD"
        else:
          status = "5線巡航中"
          signal = "HOLD"

        stock_results.append({
            "ticker": code,
            "name": name,
            "price": int(curr_close),
            "breakout_score": breakout_score,
            "soba_score": 60,
            "total_score": 140,
            "cost_label": f"買{buy_price}",
            "status": status,
            "signal": signal,
            "is_holding": True,
            "chart_url": chart_url,
        })
        continue

      # 相場流ベーススコア計算
      soba_score = 0
      if ma20_slope >= 0:
        soba_score += 20
      if is_ppp:
        soba_score += 25
      if is_mono:
        soba_score += 15
      if is_kuchibashi:
        soba_score += 15
      if is_dense and is_yang:
        soba_score += 20
      if body_ratio > 0.55 and is_yang:
        soba_score += 10
      if is_kahanshin:
        soba_score += 30

      soba_score = min(100, max(0, soba_score))

      # ==========================================
      # ★ トータル総合判定（オニール × 相場流の融合）
      # ==========================================
      is_strong_total = (breakout_score >= 40) and (soba_score >= 85)

      if bias_20 > 8.0:
        status = "過熱乖離"
        signal = "NONE"
        soba_score = 45
      elif is_strong_total:
        # 新高値40点以上 かつ 相場流85点以上の本命銘柄だけに★を点灯！
        if is_kahanshin:
          status = "★即買(下半身)"
        else:
          status = "★即買(くちばし)"
        signal = "STRONG_BUY"
      elif is_kahanshin:
        if breakout_score < 40:
          status = "底値反発"  # マクアケ等、新高値条件を満たさないものは星なし
          signal = "WATCH"
        else:
          status = "下半身(買)"
          signal = "BUY"
      elif is_kuchibashi:
        if breakout_score < 40:
          status = "底値くちばし"
          signal = "WATCH"
        else:
          status = "くちばし"
          signal = "BUY"
      elif is_dense and is_yang:
        status = "線密集/初動"
        signal = "WATCH"
        soba_score = max(soba_score, 65)
      elif is_ppp and ma20_slope > 0:
        status = "PPP継続"
        signal = "WATCH"
      elif curr_close > m5_val:
        status = "5線上維持"
        signal = "NONE"
      elif curr_close < m20_val:
        status = "20線下"
        signal = "NONE"
        soba_score = 0
      else:
        status = "様子見"
        signal = "NONE"

      # トータルスコア（合算値）
      total_score = breakout_score + soba_score
      cost_man = round((curr_close * 100) / 10000, 1)

      stock_results.append({
          "ticker": code,
          "name": name,
          "price": int(curr_close),
          "breakout_score": breakout_score,
          "soba_score": soba_score,
          "total_score": total_score,
          "cost_label": f"{cost_man}万",
          "status": status,
          "signal": signal,
          "is_holding": False,
          "chart_url": chart_url,
      })
    except Exception:
      continue

  # 並び替え順：
  # 1. 保有株最優先
  # 2. ★即買フラグ（STRONG_BUY）最優先
  # 3. トータルスコア（新高値＋相場流）の合計点降順
  stock_results.sort(
      key=lambda x: (
          1 if x["is_holding"] else 0,
          1 if x["signal"] == "STRONG_BUY" else 0,
          x["total_score"],
          x["soba_score"],
      ),
      reverse=True,
  )

  top12 = stock_results[:12]

  output_data = {
      "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "count": len(top12),
      "stocks": top12,
  }

  with open("watchlist.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

  print(
      f"スクリーニング完了: 全112銘柄からトータル判定トップ12銘柄を watchlist.json"
      " に出力しました。"
  )


if __name__ == "__main__":
  run_screening()
