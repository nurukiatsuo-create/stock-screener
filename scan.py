import json
from datetime import datetime

import numpy as np
import pandas as pd
import pytz
import yfinance as yf


# ============================================================
# 監視ユニバース（現行80銘柄）
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


# ============================================================
# 銘柄名
# Scriptable側の既存辞書と整合
# ============================================================
STOCK_NAMES = {
    "7826.T": "フルヤ金属",
    "6912.T": "菊水HD",
    "9249.T": "日本エコ",
    "7192.T": "日モーゲージ",
    "6727.T": "ワコム",
    "6364.T": "北越工業",
    "3560.T": "ほぼ日",
    "5957.T": "日東精工",
    "7172.T": "JIA",
    "1401.T": "エムビーエス",
    "6652.T": "IDEC",
    "6345.T": "アイチコーポ",
    "6862.T": "ミナトHD",
    "6855.T": "日電子材料",
    "6407.T": "CKD",
    "6134.T": "FUJI",
    "6629.T": "テクノホライ",
    "6226.T": "守谷輸送機",
    "6904.T": "原田工業",
    "6368.T": "オルガノ",
    "6941.T": "山一電機",
    "6946.T": "日アビオ",
    "6866.T": "日置電機",
    "7254.T": "ユニバンス",
    "6258.T": "平田機工",
    "6518.T": "三相電機",
    "6616.T": "トレックス",
    "6677.T": "SKエレク",
    "6474.T": "不二越",
    "6327.T": "北川精機",
    "7715.T": "長野計器",
    "6508.T": "明電舎",
    "4776.T": "サイボウズ",
    "3923.T": "ラクス",
    "6027.T": "弁護士ドット",
    "3663.T": "セルシス",
    "3968.T": "セグエ",
    "5033.T": "ヌーラボ",
    "4055.T": "T&S",
    "5254.T": "Arent",
    "4828.T": "Bエンジニア",
    "4825.T": "ウェザーニュー",
    "4258.T": "網屋",
    "3692.T": "FFRI",
    "4012.T": "アクシス",
    "3763.T": "プロシップ",
    "7094.T": "NexTone",
    "3696.T": "セレス",
    "3040.T": "ソリトン",
    "4440.T": "ヴィッツ",
    "4371.T": "C＆C",
    "4414.T": "フレクト",
    "4396.T": "システムサポ",
    "5591.T": "AVILEN",
    "6998.T": "日タングステン",
    "6871.T": "日マイクロ",
    "6787.T": "メイコー",
    "4368.T": "扶桑化学",
    "4369.T": "トリケミカル",
    "4975.T": "JCU",
    "4626.T": "太陽HD",
    "4971.T": "メック",
    "4046.T": "大阪ソーダ",
    "3441.T": "サンコーテクノ",
    "3449.T": "テクノフレ",
    "4970.T": "東洋合成",
    "5805.T": "SWCC",
    "7609.T": "ダイトロン",
    "4461.T": "第一工薬",
    "7781.T": "平山HD",
    "5018.T": "MORESCO",
    "4100.T": "戸田工業",
    "3482.T": "ロードスター",
    "3498.T": "霞ヶ関キャピ",
    "7148.T": "FPG",
    "2884.T": "ヨシムラFD",
    "5136.T": "tripla",
    "7372.T": "デコルテHD",
    "5589.T": "オートサーバ",
    "4765.T": "SBIGアセット",
}


# ============================================================
# 四季報 fund_score
# ------------------------------------------------------------
# 現在アップロード済み資料で数値として確認できるものだけ登録。
#
# 未登録銘柄を自動的に85点などとは扱わない。
#
# 通常の新高値発射台：
#     fund_score >= 85 が確認できた銘柄のみ
#
# PF4.11探索：
#     当時の入口条件にfund_scoreがなかったため、
#     全80銘柄を対象としてよい
# ============================================================
FUND_SCORES = {
    "7826.T": 100,  # フルヤ金属
    "6862.T": 100,  # ミナトHD
    "4765.T": 100,  # SBIGアセット
    "4258.T": 100,  # 網屋

    "6998.T": 85,   # 日本タングステン
    "6652.T": 85,   # IDEC
    "6258.T": 85,   # 平田機工
    "1401.T": 85,   # エムビーエス
    "6345.T": 85,   # アイチコーポ

    "5957.T": 80,   # 日東精工
    "6364.T": 80,   # 北越工業

    "7192.T": 90,   # 日本モーゲージサービス
}


# ============================================================
# 設定値
# ============================================================
HISTORY_PERIOD = "2y"
INTERVAL = "1d"

# 大引け15:30後、データ安定待ちを含めて16時から当日足を利用
DAILY_BAR_CONFIRM_HOUR_JST = 16

# 当日足 + 前日までの250営業日
MIN_HISTORY_ROWS = 251

# PF4.11探索群の既存条件
PF411_MIN_HISTORY_ROWS = 260

# 流動性フィルター
# これはPF4.11条件には適用しない
MIN_AVG_TURNOVER = 40_000_000

# 四季報
FUND_SCORE_MIN = 85

# 通常発射台
LAUNCHPAD_MIN_OFF_HIGH = -6.0
LAUNCHPAD_MAX_OFF_HIGH = 3.0

# PF4.11探索
PF411_MIN_OFF_HIGH = -3.0
PF411_MAX_OFF_HIGH = 0.0
PF411_VOLUME_RATIO = 1.2

# 通常ボードでは運用リスク対策として流動性をチェック
APPLY_TURNOVER_FILTER_TO_NORMAL_BOARDS = True


# ============================================================
# 共通ユーティリティ
# ============================================================
def clean_code(ticker):
    return ticker.replace(".T", "")


def get_name(ticker):
    return STOCK_NAMES.get(ticker, clean_code(ticker))


def extract_ticker_frame(downloaded, ticker):
    """
    yf.download(group_by="ticker") の結果から
    1銘柄分のOHLCVを安全に取り出す。
    """
    if downloaded is None or downloaded.empty:
        return pd.DataFrame()

    if isinstance(downloaded.columns, pd.MultiIndex):
        level0 = downloaded.columns.get_level_values(0)

        if ticker not in level0:
            return pd.DataFrame()

        df = downloaded[ticker].copy()

    else:
        # 単一銘柄取得時への保険
        df = downloaded.copy()

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    if not all(col in df.columns for col in required):
        return pd.DataFrame()

    return df[required].copy()


def keep_confirmed_daily_bars(df, now_jst):
    """
    日足未確定時間帯には当日足を使用しない。

    JST 16:00より前：
        当日足を除外

    JST 16:00以降：
        当日足を使用可能
    """
    if df.empty:
        return df

    df = df.sort_index().copy()

    dates = pd.DatetimeIndex(df.index)

    if dates.tz is not None:
        dates_for_compare = dates.tz_convert("Asia/Tokyo")
    else:
        dates_for_compare = dates

    if now_jst.hour < DAILY_BAR_CONFIRM_HOUR_JST:

        mask = np.array([
            d.date() < now_jst.date()
            for d in dates_for_compare
        ])

        df = df.loc[mask]

    return df


def calculate_prior_250_high(df):
    """
    最新足を除外し、
    直前250営業日のHighの最大値を返す。

    当日のHighは絶対に基準高値へ含めない。
    """
    if len(df) < MIN_HISTORY_ROWS:
        return None

    prior_highs = df["High"].iloc[-251:-1]

    values = prior_highs.to_numpy(dtype=float)

    if len(values) != 250:
        return None

    if not np.isfinite(values).all():
        return None

    if (values <= 0).any():
        return None

    return float(np.max(values))


def calc_off_high(close, prior_high):
    """
    前日までの250営業日高値からの乖離率。

    例：
      -2% → 高値まであと2%
      +1% → 高値を1%上抜け
    """
    if (
        prior_high is None
        or prior_high <= 0
        or not np.isfinite(close)
    ):
        return None

    return (
        (close - prior_high)
        / prior_high
        * 100.0
    )


# ============================================================
# PF4.11探索条件
# ============================================================
def matches_pf411_prebreakout(
    off_high,
    close,
    sma50,
    volume,
    vol20,
    history_rows
):
    """
    PF4.11バックテストで使用した
    「新高値直前群」の入口条件。

    条件
    ----
    -3.0% <= off_high < 0%
    Close > SMA50
    Volume >= VolSMA20 * 1.2
    履歴260行以上

    注意
    ----
    これは「候補抽出条件」。

    PF4.11そのものを再現するには、
    翌営業日始値エントリー、
    利確、
    損切り、
    最大保有日数、
    同時シグナル時の優先順位、
    資金配分などが別途必要。
    """

    return (
        history_rows >= PF411_MIN_HISTORY_ROWS

        and off_high is not None
        and np.isfinite(off_high)

        and PF411_MIN_OFF_HIGH
        <= off_high
        < PF411_MAX_OFF_HIGH

        and np.isfinite(sma50)
        and close > sma50

        and np.isfinite(vol20)
        and vol20 > 0

        and volume >= vol20 * PF411_VOLUME_RATIO
    )


# ============================================================
# 通常の新高値発射台
# ============================================================
def evaluate_launchpad(
    off_high,
    volume,
    vol20,
    fund_score
):
    """
    本番の通常新高値ボード。

    条件
    ----
    四季報 fund_score >= 85

    高値差
    -6% ～ 0% ：発射台
     0% ～ +3%：ブレイク確認
     +3%超     ：見送り

    fund_score未確認銘柄は
    勝手に85点扱いしない。
    """

    if (
        off_high is None
        or not np.isfinite(off_high)
    ):
        return 0, "判定不能"

    # +3%超
    if off_high > LAUNCHPAD_MAX_OFF_HIGH:
        return 0, "見送り"

    # -6%より下
    if off_high < LAUNCHPAD_MIN_OFF_HIGH:
        return 0, "助走"

    # 四季報スコア未確認
    if fund_score is None:
        return 0, "業績未確認"

    # 85点未満
    if fund_score < FUND_SCORE_MIN:
        return 0, "業績足切り"

    # 出来高加点
    if (
        np.isfinite(vol20)
        and vol20 > 0
    ):
        vol_ratio = volume / vol20
    else:
        vol_ratio = 0.0

    nh_score = 85

    if vol_ratio > 1.2:
        nh_score += 5

    # 0%同値は未突破
    if off_high > 0:
        status = "★ブレイク確認"
    else:
        status = "★発射台"

    return nh_score, status


# ============================================================
# 相場流ランキング用
# 純テクニカル新高値スコア
# ============================================================
def evaluate_technical_new_high(
    close,
    sma50,
    off_high,
    volume,
    vol20
):
    """
    相場流×新高値ランキング用。

    四季報fund_scoreとは分離して、
    テクニカルだけを評価する。

    相場流60%
    ＋
    新高値テクニカル40%

    の互換用。
    """

    score = 50

    # 上昇トレンド
    if (
        np.isfinite(sma50)
        and close > sma50
    ):
        score += 15

    # 高値までの距離
    if (
        off_high is not None
        and np.isfinite(off_high)
    ):

        if -3.0 <= off_high <= 2.5:
            score += 20

        elif -6.0 <= off_high < -3.0:
            score += 10

        elif off_high > 3.0:
            score -= 20

    # 出来高増加
    if (
        np.isfinite(vol20)
        and vol20 > 0
        and volume >= vol20 * 1.3
    ):
        score += 15

    return min(
        max(score, 0),
        100
    )


# ============================================================
# 相場流パターン判定
# 旧簡略版ではなく厳格版へ復元
# ============================================================
def evaluate_soba_pattern(df):

    if len(df) < 100:
        return 50, "データ不足"

    closes = df["Close"]

    sma5 = closes.rolling(5).mean()
    sma20 = closes.rolling(20).mean()
    sma60 = closes.rolling(60).mean()
    sma100 = closes.rolling(100).mean()

    latest = df.iloc[-1]

    c_open = float(latest["Open"])
    c_close = float(latest["Close"])

    s5 = float(sma5.iloc[-1])
    s20 = float(sma20.iloc[-1])
    s60 = float(sma60.iloc[-1])
    s100 = float(sma100.iloc[-1])

    p5 = float(sma5.iloc[-2])
    p20 = float(sma20.iloc[-2])

    vals = [
        c_open,
        c_close,
        s5,
        s20,
        s60,
        s100,
        p5,
        p20
    ]

    if not all(
        np.isfinite(v)
        for v in vals
    ):
        return 50, "データ不足"

    sma5_slope = s5 - p5
    sma20_slope = s20 - p20

    # --------------------------------------------------------
    # ① 下半身
    #
    # ・陽線
    # ・始値が5日線下
    # ・終値が5日線上
    # ・実体の半分以上が5日線上
    # ・5日線が横ばい～上向き
    # --------------------------------------------------------
    is_lower_half = (
        c_close > c_open

        and c_open < s5 < c_close

        and (
            (c_close - s5)
            >
            (s5 - c_open)
        )

        and sma5_slope >= 0
    )

    # --------------------------------------------------------
    # ② くちばし
    # --------------------------------------------------------
    is_beak = (

        (
            p5 <= p20
            and s5 > s20
            and sma5_slope > 0
        )

        or

        (
            s5 > s20

            and (
                (s5 - s20)
                >
                (p5 - p20)
            )

            and sma20_slope > 0

            and (
                abs(s5 - s20)
                / c_close
                < 0.03
            )
        )
    )

    # --------------------------------------------------------
    # ③ 線密集
    # 5日・20日・60日線が3.5%以内
    # --------------------------------------------------------
    ma_range = (
        max(s5, s20, s60)
        -
        min(s5, s20, s60)
    )

    is_dense = (
        (ma_range / c_close) < 0.035
        and c_close > s5
    )

    # --------------------------------------------------------
    # ④ PPP
    # --------------------------------------------------------
    is_ppp = (
        s5
        >
        s20
        >
        s60
        >
        s100
    )

    # --------------------------------------------------------
    # スコア
    # --------------------------------------------------------
    if is_lower_half:
        return 100, "★即買(下半身)"

    if is_beak:
        return 90, "くちばし"

    if is_dense:
        return 80, "線密集/初動"

    if is_ppp:
        return 70, "PPP継続"

    if c_close > s5:
        return 60, "5日線上推移"

    return 45, "調整/陰線"


# ============================================================
# メイン
# ============================================================
def analyze_market():

    jst = pytz.timezone("Asia/Tokyo")

    now_jst = datetime.now(jst)

    updated_str = now_jst.strftime(
        "%m/%d %H:%M"
    )

    print(
        f">>> スクリーニング開始: "
        f"{updated_str}"
    )

    print(
        f">>> 監視銘柄数: "
        f"{len(TICKERS)}"
    )


    # ========================================================
    # 株価データ一括取得
    #
    # 旧コードの
    # Ticker().history()
    # Ticker().info
    # の80回逐次通信を廃止
    # ========================================================
    downloaded = yf.download(
        TICKERS,

        period=HISTORY_PERIOD,

        interval=INTERVAL,

        group_by="ticker",

        auto_adjust=True,

        actions=False,

        threads=True,

        progress=False,
    )


    new_high_candidates = []

    soba_candidates = []

    pf411_candidates = []

    skipped = []


    # ========================================================
    # 各銘柄
    # ========================================================
    for ticker in TICKERS:

        try:

            # ------------------------------------------------
            # 1. データ抽出
            # ------------------------------------------------
            df = extract_ticker_frame(
                downloaded,
                ticker
            )

            if df.empty:

                skipped.append({
                    "ticker": ticker,
                    "reason": "データ取得失敗"
                })

                continue


            # ------------------------------------------------
            # 2. 未確定当日足を除外
            # ------------------------------------------------
            df = keep_confirmed_daily_bars(
                df,
                now_jst
            )


            # ------------------------------------------------
            # 3. 欠損除去
            # ------------------------------------------------
            df = df.dropna(
                subset=[
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume"
                ]
            ).copy()

            df = df.sort_index()


            # 相場流最低限
            if len(df) < 60:

                skipped.append({
                    "ticker": ticker,
                    "reason":
                        f"履歴不足({len(df)}行)"
                })

                continue


            # ------------------------------------------------
            # 4. 最新足
            # ------------------------------------------------
            latest = df.iloc[-1]

            close = float(
                latest["Close"]
            )

            open_p = float(
                latest["Open"]
            )

            volume = float(
                latest["Volume"]
            )


            # ------------------------------------------------
            # 価格異常チェック
            # ------------------------------------------------
            if not all(
                np.isfinite(v) and v > 0
                for v in [
                    close,
                    open_p
                ]
            ):

                skipped.append({
                    "ticker": ticker,
                    "reason": "価格データ異常"
                })

                continue


            if (
                not np.isfinite(volume)
                or volume < 0
            ):

                skipped.append({
                    "ticker": ticker,
                    "reason": "出来高データ異常"
                })

                continue


            closes = df["Close"]

            volumes = df["Volume"]


            # ------------------------------------------------
            # 5. SMA50
            # ------------------------------------------------
            if len(df) >= 50:

                sma50 = float(
                    closes
                    .rolling(50)
                    .mean()
                    .iloc[-1]
                )

            else:

                sma50 = np.nan


            # ------------------------------------------------
            # 6. 20日出来高平均
            #
            # 現行PF4.11条件との互換性のため
            # 当日を含むrolling(20)を維持
            # ------------------------------------------------
            if len(df) >= 20:

                vol20 = float(
                    volumes
                    .rolling(20)
                    .mean()
                    .iloc[-1]
                )

            else:

                vol20 = np.nan


            if (
                np.isfinite(vol20)
                and vol20 > 0
            ):

                vol_ratio = (
                    volume
                    /
                    vol20
                )

            else:

                vol_ratio = 0.0


            # ------------------------------------------------
            # 7. 前日までの250営業日高値
            # ------------------------------------------------
            prior_high250 = (
                calculate_prior_250_high(df)
            )


            # ------------------------------------------------
            # 8. 高値乖離率
            # ------------------------------------------------
            off_high = calc_off_high(
                close,
                prior_high250
            )


            # ------------------------------------------------
            # 9. 5日平均売買代金
            # ------------------------------------------------
            avg_turnover_5d = float(

                (
                    df["Close"].tail(5)
                    *
                    df["Volume"].tail(5)
                ).mean()

            )


            liquidity_ok = (

                np.isfinite(
                    avg_turnover_5d
                )

                and

                avg_turnover_5d
                >=
                MIN_AVG_TURNOVER

            )


            # ------------------------------------------------
            # 10. 基本情報
            # ------------------------------------------------
            signal_date = (
                pd.Timestamp(
                    df.index[-1]
                )
                .strftime("%Y-%m-%d")
            )

            code = clean_code(
                ticker
            )

            name = get_name(
                ticker
            )

            fund_score = (
                FUND_SCORES
                .get(ticker)
            )


            # =================================================
            # A. PF4.11探索群
            #
            # ここは通常発射台とは完全分離
            # =================================================
            if matches_pf411_prebreakout(

                off_high=off_high,

                close=close,

                sma50=sma50,

                volume=volume,

                vol20=vol20,

                history_rows=len(df)

            ):

                pf411_candidates.append({

                    "code":
                        code,

                    "name":
                        name,

                    "price":
                        int(round(close)),

                    "off_high":
                        round(
                            off_high,
                            2
                        ),

                    "vol_ratio":
                        round(
                            vol_ratio,
                            2
                        ),

                    "sma50":
                        round(
                            sma50,
                            2
                        ),

                    "avg_turnover_5d":
                        int(
                            round(
                                avg_turnover_5d
                            )
                        ),

                    # 参考表示のみ
                    # PF4.11判定には使わない
                    "fund_score":
                        fund_score,

                    "signal_date":
                        signal_date,

                    "signal_conditions":
                        (
                            "-3.0%<=off_high<0%, "
                            "close>SMA50, "
                            "volume>=VolSMA20*1.2"
                        )
                })


            # =================================================
            # 250日高値が計算できない場合
            # 新高値関連ランキングから除外
            # =================================================
            if off_high is None:

                skipped.append({
                    "ticker": ticker,
                    "reason":
                        "前日までの250営業日高値を計算不能"
                })

                continue


            # =================================================
            # B. 相場流 × 新高値テクニカル
            # =================================================
            soba_score, soba_pattern = (
                evaluate_soba_pattern(df)
            )


            tech_nh_score = (
                evaluate_technical_new_high(

                    close=close,

                    sma50=sma50,

                    off_high=off_high,

                    volume=volume,

                    vol20=vol20
                )
            )


            # +3%以上に過熱した銘柄は除外
            if (
                off_high
                <=
                LAUNCHPAD_MAX_OFF_HIGH
            ):

                if (
                    not
                    APPLY_TURNOVER_FILTER_TO_NORMAL_BOARDS

                    or

                    liquidity_ok
                ):

                    if soba_score >= 70:

                        total_score = (
                            soba_score * 0.6
                            +
                            tech_nh_score * 0.4
                        )


                        soba_candidates.append({

                            "code":
                                code,

                            "name":
                                name,

                            "price":
                                int(round(close)),

                            "soba_score":
                                soba_score,

                            "nh_score":
                                tech_nh_score,

                            "total_score":
                                round(
                                    total_score,
                                    1
                                ),

                            "soba_pattern":
                                soba_pattern,

                            "off_high":
                                round(
                                    off_high,
                                    2
                                ),

                            "fund_score":
                                fund_score,

                            "signal_date":
                                signal_date,
                        })


            # =================================================
            # C. 通常の新高値発射台
            # =================================================
            launch_score, launch_status = (
                evaluate_launchpad(

                    off_high=off_high,

                    volume=volume,

                    vol20=vol20,

                    fund_score=fund_score
                )
            )


            if launch_status in (
                "★発射台",
                "★ブレイク確認"
            ):

                if (
                    not
                    APPLY_TURNOVER_FILTER_TO_NORMAL_BOARDS

                    or

                    liquidity_ok
                ):

                    new_high_candidates.append({

                        "code":
                            code,

                        "name":
                            name,

                        "price":
                            int(round(close)),

                        "nh_score":
                            launch_score,

                        "fund_score":
                            fund_score,

                        "off_high":
                            round(
                                off_high,
                                2
                            ),

                        "vol_ratio":
                            round(
                                vol_ratio,
                                2
                            ),

                        "status":
                            launch_status,

                        "avg_turnover_5d":
                            int(
                                round(
                                    avg_turnover_5d
                                )
                            ),

                        "signal_date":
                            signal_date,
                    })


        except Exception as e:

            skipped.append({

                "ticker":
                    ticker,

                "reason":
                    f"例外: {e}"

            })

            print(
                f"エラー発生 "
                f"({ticker}): {e}"
            )


    # ========================================================
    # ランキング
    # ========================================================

    # --------------------------------------------------------
    # 1. 通常発射台
    #
    # nh_score優先
    # ↓
    # 高値差0%に近い順
    # ↓
    # 出来高倍率
    # --------------------------------------------------------
    new_high_candidates.sort(

        key=lambda x: (

            x["nh_score"],

            -abs(
                x["off_high"]
            ),

            x["vol_ratio"],

        ),

        reverse=True
    )


    # --------------------------------------------------------
    # 2. 相場流
    #
    # 相場流60%
    # 新高値テクニカル40%
    # --------------------------------------------------------
    soba_candidates.sort(

        key=lambda x: (

            x["total_score"],

            x["soba_score"],

            x["nh_score"]

        ),

        reverse=True
    )


    # --------------------------------------------------------
    # 3. PF4.11探索群
    #
    # まず0%に近い順
    # 次に出来高倍率
    # --------------------------------------------------------
    pf411_candidates.sort(

        key=lambda x: (

            x["off_high"],

            x["vol_ratio"]

        ),

        reverse=True
    )


    # ========================================================
    # fund_score確認状況
    # ========================================================
    confirmed_fund_count = sum(

        1

        for ticker in TICKERS

        if FUND_SCORES.get(
            ticker
        ) is not None
    )


    fund85_count = sum(

        1

        for ticker in TICKERS

        if (
            FUND_SCORES.get(
                ticker
            )
            or 0
        )
        >=
        FUND_SCORE_MIN
    )


    # ========================================================
    # JSON
    # ========================================================
    output_data = {

        "updated_at":
            updated_str,


        # ----------------------------------------------------
        # データポリシー
        # ----------------------------------------------------
        "data_policy": {

            "daily_bar":
                (
                    "JST16:00より前は"
                    "当日足を除外"
                ),

            "price_adjustment":
                (
                    "yfinance "
                    "auto_adjust=True"
                ),

            "high_reference":
                (
                    "最新足を除く"
                    "直前250営業日の"
                    "High最大値"
                )
        },


        # ----------------------------------------------------
        # ユニバース状況
        # ----------------------------------------------------
        "universe": {

            "ticker_count":
                len(TICKERS),

            "confirmed_fund_score_count":
                confirmed_fund_count,

            "fund_score_85plus_count":
                fund85_count
        },


        # ----------------------------------------------------
        # 通常新高値
        # ----------------------------------------------------
        "new_high_ranks":
            new_high_candidates[:10],


        # ----------------------------------------------------
        # 相場流
        # ----------------------------------------------------
        "soba_ranks":
            soba_candidates[:10],


        # ----------------------------------------------------
        # PF4.11探索
        # ----------------------------------------------------
        "pf411_ranks":
            pf411_candidates,


        # ----------------------------------------------------
        # 通常新高値の説明
        # ----------------------------------------------------
        "new_high_reference": {

            "label":
                (
                    "通常の新高値"
                    "発射台/ブレイク確認"
                ),

            "conditions": [

                (
                    "確認済み四季報 "
                    "fund_score >= 85"
                ),

                (
                    "-6.0% <= "
                    "off_high <= +3.0%"
                ),

                (
                    "off_high <= 0% は発射台、"
                    "0%超はブレイク確認"
                ),

                (
                    "+3.0%超は見送り"
                ),

                (
                    f"5日平均売買代金 >= "
                    f"{MIN_AVG_TURNOVER:,}円"
                    "（運用流動性フィルター）"
                    if
                    APPLY_TURNOVER_FILTER_TO_NORMAL_BOARDS
                    else
                    "売買代金フィルターなし"
                )
            ],

            "fund_score_note":
                (
                    "FUND_SCORESに数値がない銘柄は"
                    "通常発射台へ入れない。"
                    "推測値やyfinanceの動的"
                    "ファンダメンタルズで代替しない。"
                )
        },


        # ----------------------------------------------------
        # PF4.11の説明
        # ----------------------------------------------------
        "pf411_reference": {

            "label":
                (
                    "PF4.11過去バックテストの"
                    "入口条件に対応する当日候補。"
                    "PF4.11自体を再計算したものではない。"
                ),

            "conditions": [

                "-3.0% <= off_high < 0.0%",

                "終値 > SMA50",

                (
                    "当日出来高 >= "
                    "20日平均出来高 * 1.2"
                ),

                "過去データ260行以上"
            ],

            "execution_note":
                (
                    "過去バックテストの売買再現には、"
                    "翌営業日始値エントリー、出口、"
                    "保有期間、同時シグナル時の"
                    "資金配分等を別途一致させる必要がある。"
                ),

            "limitations":
                (
                    "このリストにはfund_score・PBR・"
                    "売買代金の足切りを後付けしない。"
                    "PF4.11は過去の探索値であり"
                    "将来成績を示さない。"
                )
        },


        # ----------------------------------------------------
        # スキップ情報
        # ----------------------------------------------------
        "skipped":
            skipped
    }


    # ========================================================
    # 保存
    # ========================================================
    with open(
        "stocks_data.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output_data,
            f,
            ensure_ascii=False,
            indent=2
        )


    # ========================================================
    # コンソール
    # ========================================================
    print(

        ">>> 完了: "
        "stocks_data.json を生成しました。"

        f" 発射台="
        f"{len(new_high_candidates)}銘柄 /"

        f" 相場流="
        f"{len(soba_candidates)}銘柄 /"

        f" PF4.11入口条件="
        f"{len(pf411_candidates)}銘柄 /"

        f" スキップ="
        f"{len(skipped)}件"
    )


# ============================================================
# 実行
# ============================================================
if __name__ == "__main__":
    analyze_market()
