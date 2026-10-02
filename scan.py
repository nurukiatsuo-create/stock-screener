import json
from datetime import datetime

import numpy as np
import pandas as pd
import pytz
import yfinance as yf


# ============================================================
# 監視ユニバース：現行80銘柄
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
    "3482.T", "3498.T", "7148.T", "2884.T", "5136.T", "7372.T", "5589.T", "4765.T",
]


# ============================================================
# 銘柄名
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
#
# 現時点で数値確認済みのものだけ登録。
#
# 重要：
# ・未登録銘柄も発射台判定対象
# ・fund_scoreは現時点では参考表示のみ
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

    "7192.T": 90,   # 日本モーゲージ
}


# ============================================================
# 設定
# ============================================================

HISTORY_PERIOD = "2y"
INTERVAL = "1d"

# 東証大引け15:30後、
# データ安定待ちを含めて16:00以降に当日足を利用
DAILY_BAR_CONFIRM_HOUR_JST = 16

# 最新足 + 前日まで250営業日
MIN_HISTORY_ROWS = 251

# PF4.11探索用
PF411_MIN_HISTORY_ROWS = 260

# 通常の発射台・ブレイク候補に使用する最低5日平均売買代金
MIN_AVG_TURNOVER = 40_000_000

# 通常発射台
LAUNCHPAD_MIN_OFF_HIGH = -6.0
LAUNCHPAD_MAX_OFF_HIGH = 3.0

# PF4.11探索
PF411_MIN_OFF_HIGH = -3.0
PF411_MAX_OFF_HIGH = 0.0
PF411_VOLUME_RATIO = 1.2

# 発射台・ブレイク確認には流動性フィルターを適用
# 95点見送りには適用しない
APPLY_TURNOVER_FILTER_TO_ACTIVE_CANDIDATES = True

# 観察用の暫定定義。売買・採点には使用しない。
# これは値幅制約による持ち合いの近似であり、Darvas boxの認定ではない。
BOX_MIN_BARS = 10
BOX_MAX_BARS = 60
BOX_MAX_WIDTH_PCT = 15.0
BOX_RECENT_BARS = 5


def calculate_box_metrics(df):
    """最新の判定足を除く過去足だけで、持ち合いの観察値を計算する。

    duration_bars: 末尾から遡り、幅15%以内に収まる最長10〜60本。
    width_pct: (期間高値 - 期間安値) / 期間高値 * 100。
    contraction_ratio: 直近5本のwidth_pct / その前5本のwidth_pct。
    1未満なら縮小。ゼロ幅の比較元・履歴不足・異常値はnull。
    本数は有効な日足観測数。取引所カレンダーによる欠落日は補完しない。
    """
    result = {
        "status": "insufficient_history",
        "as_of": None,
        "available_prior_bars": max(len(df) - 1, 0),
        "duration_bars": None,
        "duration_capped": False,
        "start_date": None,
        "upper": None,
        "lower": None,
        "width_pct": None,
        "width_20d_pct": None,
        "recent_5d_width_pct": None,
        "previous_5d_width_pct": None,
        "contraction_ratio": None,
        "is_contracting": None,
    }
    if not {"High", "Low"}.issubset(df.columns):
        result["status"] = "invalid_data"
        return result
    if len(df) < BOX_MIN_BARS + 1:
        return result
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        result["status"] = "invalid_data"
        return result

    prior = df.iloc[:-1].tail(BOX_MAX_BARS)
    try:
        highs = prior["High"].to_numpy(dtype=float)
        lows = prior["Low"].to_numpy(dtype=float)
        valid = (np.isfinite(highs).all() and np.isfinite(lows).all()
                 and (lows > 0).all() and (highs >= lows).all())
        result["as_of"] = pd.Timestamp(prior.index[-1]).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        valid = False
    if not valid:
        result["status"] = "invalid_data"
        return result

    def width(high, low):
        return float((high.max() - low.min()) / high.max() * 100.0)

    recent = width(highs[-BOX_RECENT_BARS:], lows[-BOX_RECENT_BARS:])
    previous = width(highs[-2 * BOX_RECENT_BARS:-BOX_RECENT_BARS],
                     lows[-2 * BOX_RECENT_BARS:-BOX_RECENT_BARS])
    result["recent_5d_width_pct"] = round(recent, 4)
    result["previous_5d_width_pct"] = round(previous, 4)
    if previous > 0:
        ratio = recent / previous
        result["contraction_ratio"] = round(ratio, 4)
        result["is_contracting"] = bool(ratio < 1.0)
    if len(prior) >= 20:
        result["width_20d_pct"] = round(width(highs[-20:], lows[-20:]), 4)

    result["status"] = "no_range_within_limit"
    for bars in range(len(prior), BOX_MIN_BARS - 1, -1):
        upper = float(highs[-bars:].max())
        lower = float(lows[-bars:].min())
        depth = (upper - lower) / upper * 100.0
        if depth <= BOX_MAX_WIDTH_PCT:
            result.update({
                "status": "flat_range" if depth == 0 else "range_candidate",
                "duration_bars": bars,
                "duration_capped": bars == BOX_MAX_BARS,
                "start_date": pd.Timestamp(prior.index[-bars]).strftime("%Y-%m-%d"),
                "upper": upper,
                "lower": lower,
                "width_pct": round(depth, 4),
            })
            break
    return result


# ============================================================
# 共通ユーティリティ
# ============================================================

def clean_code(ticker):
    return ticker.replace(".T", "")


def get_name(ticker):
    return STOCK_NAMES.get(
        ticker,
        clean_code(ticker)
    )


def extract_ticker_frame(downloaded, ticker):
    """
    yf.download(group_by="ticker")から
    1銘柄分のOHLCVを取り出す。
    """

    if downloaded is None or downloaded.empty:
        return pd.DataFrame()

    if isinstance(
        downloaded.columns,
        pd.MultiIndex
    ):

        level0 = (
            downloaded
            .columns
            .get_level_values(0)
        )

        if ticker not in level0:
            return pd.DataFrame()

        df = downloaded[ticker].copy()

    else:
        df = downloaded.copy()

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    if not all(
        col in df.columns
        for col in required
    ):
        return pd.DataFrame()

    return df[required].copy()


def keep_confirmed_daily_bars(
    df,
    now_jst
):
    """
    JST 16:00より前なら当日足を除外。
    """

    if df.empty:
        return df

    df = (
        df
        .sort_index()
        .copy()
    )

    dates = pd.DatetimeIndex(
        df.index
    )

    if dates.tz is not None:
        compare_dates = (
            dates
            .tz_convert("Asia/Tokyo")
        )
    else:
        compare_dates = dates

    if (
        now_jst.hour
        <
        DAILY_BAR_CONFIRM_HOUR_JST
    ):

        mask = np.array([
            d.date()
            <
            now_jst.date()

            for d in compare_dates
        ])

        df = df.loc[mask]

    return df


def calculate_prior_250_high(df):
    """
    最新足を除外した直前250営業日の
    High最大値。

    当日のHighは基準高値に含めない。
    """

    if len(df) < MIN_HISTORY_ROWS:
        return None

    prior_highs = (
        df["High"]
        .iloc[-251:-1]
    )

    values = (
        prior_highs
        .to_numpy(dtype=float)
    )

    if len(values) != 250:
        return None

    if not np.isfinite(values).all():
        return None

    if (values <= 0).any():
        return None

    return float(
        np.max(values)
    )


def calc_off_high(
    close,
    prior_high
):
    """
    前日までの250営業日高値からの乖離率。

    -2% = 高値まであと2%
    +1% = 高値を1%上抜け
    """

    if (
        prior_high is None
        or prior_high <= 0
        or not np.isfinite(close)
    ):
        return None

    return (
        (close - prior_high)
        /
        prior_high
        *
        100.0
    )


def calc_vol20(df):
    """
    PF4.11既存条件との整合のため、
    最新足を含むrolling(20)。
    """

    if len(df) < 20:
        return np.nan

    return float(
        df["Volume"]
        .rolling(20)
        .mean()
        .iloc[-1]
    )


def calc_avg_turnover_5d(df):
    """
    直近5営業日の平均売買代金。
    """

    if len(df) < 5:
        return np.nan

    return float(
        (
            df["Close"].tail(5)
            *
            df["Volume"].tail(5)
        ).mean()
    )


# ============================================================
# PF4.11入口条件
# ============================================================

def matches_pf411_prebreakout(
    off_high,
    close,
    sma50,
    volume,
    vol20,
    history_rows,
):
    """
    PF4.11過去バックテストの
    入口条件に対応する候補抽出。

    -3.0% <= off_high < 0%
    Close > SMA50
    Volume >= VolSMA20 × 1.2
    履歴260行以上
    """

    return (

        history_rows
        >=
        PF411_MIN_HISTORY_ROWS

        and off_high is not None
        and np.isfinite(off_high)

        and
        PF411_MIN_OFF_HIGH
        <= off_high
        < PF411_MAX_OFF_HIGH

        and np.isfinite(sma50)
        and close > sma50

        and np.isfinite(vol20)
        and vol20 > 0

        and
        volume
        >=
        vol20 * PF411_VOLUME_RATIO
    )


# ============================================================
# 通常新高値判定
#
# 85点：
#   発射台 / ブレイク基本条件
#
# 90点：
#   上記 + 出来高1.2倍超
#
# 95点：
#   +3%超で過熱
#   新規買いは見送り
#   観察用として表示
#
# ※95は90より「良い」という意味ではない
# ============================================================

def evaluate_launchpad(
    close,
    sma50,
    off_high,
    volume,
    vol20,
):

    if (
        off_high is None
        or not np.isfinite(off_high)
    ):
        return 0, "判定不能"

    # --------------------------------------------------------
    # 50MAより下
    # --------------------------------------------------------

    if (
        not np.isfinite(sma50)
        or close <= sma50
    ):
        return 0, "50MA下"

    # --------------------------------------------------------
    # +3%超
    #
    # 過熱・見送り。
    # 流動性に関係なく観察用表示。
    # --------------------------------------------------------

    if (
        off_high
        >
        LAUNCHPAD_MAX_OFF_HIGH
    ):
        return 95, "見送り"

    # --------------------------------------------------------
    # -6%より遠い
    # --------------------------------------------------------

    if (
        off_high
        <
        LAUNCHPAD_MIN_OFF_HIGH
    ):
        return 0, "助走"

    # --------------------------------------------------------
    # 出来高倍率
    # --------------------------------------------------------

    if (
        np.isfinite(vol20)
        and vol20 > 0
    ):
        vol_ratio = (
            volume / vol20
        )
    else:
        vol_ratio = 0.0

    # --------------------------------------------------------
    # 基本85点
    # --------------------------------------------------------

    nh_score = 85

    # 出来高1.2倍超 → 90
    if vol_ratio > 1.2:
        nh_score += 5

    # --------------------------------------------------------
    # 発射台 / ブレイク
    # --------------------------------------------------------

    if off_high > 0:
        status = "★ブレイク確認"
    else:
        status = "★発射台"

    return nh_score, status


# ============================================================
# 相場流ランキング用
# 新高値テクニカル点
# ============================================================

def evaluate_technical_new_high(
    close,
    sma50,
    off_high,
    volume,
    vol20,
):

    score = 50

    # 50MA上
    if (
        np.isfinite(sma50)
        and close > sma50
    ):
        score += 15

    # 高値差
    if (
        off_high is not None
        and np.isfinite(off_high)
    ):

        if (
            -3.0
            <= off_high
            <= 2.5
        ):
            score += 20

        elif (
            -6.0
            <= off_high
            < -3.0
        ):
            score += 10

        elif off_high > 3.0:
            score -= 20

    # 出来高
    if (
        np.isfinite(vol20)
        and vol20 > 0
        and
        volume
        >=
        vol20 * 1.3
    ):
        score += 15

    return min(
        max(score, 0),
        100
    )


# ============================================================
# 相場流パターン判定
# ============================================================

def evaluate_soba_pattern(df):

    if len(df) < 100:
        return 50, "データ不足"

    closes = df["Close"]

    sma5 = (
        closes
        .rolling(5)
        .mean()
    )

    sma20 = (
        closes
        .rolling(20)
        .mean()
    )

    sma60 = (
        closes
        .rolling(60)
        .mean()
    )

    sma100 = (
        closes
        .rolling(100)
        .mean()
    )

    latest = df.iloc[-1]

    c_open = float(
        latest["Open"]
    )

    c_close = float(
        latest["Close"]
    )

    s5 = float(
        sma5.iloc[-1]
    )

    s20 = float(
        sma20.iloc[-1]
    )

    s60 = float(
        sma60.iloc[-1]
    )

    s100 = float(
        sma100.iloc[-1]
    )

    p5 = float(
        sma5.iloc[-2]
    )

    p20 = float(
        sma20.iloc[-2]
    )

    values = [
        c_open,
        c_close,
        s5,
        s20,
        s60,
        s100,
        p5,
        p20,
    ]

    if not all(
        np.isfinite(v)
        for v in values
    ):
        return 50, "データ不足"

    sma5_slope = s5 - p5
    sma20_slope = s20 - p20


    # ========================================================
    # ① 下半身
    # ========================================================

    is_lower_half = (

        c_close > c_open

        and
        c_open < s5 < c_close

        and
        (c_close - s5)
        >
        (s5 - c_open)

        and
        sma5_slope >= 0
    )


    # ========================================================
    # ② くちばし
    # ========================================================

    is_beak = (

        (
            p5 <= p20
            and s5 > s20
            and sma5_slope > 0
        )

        or

        (
            s5 > s20

            and
            (s5 - s20)
            >
            (p5 - p20)

            and
            sma20_slope > 0

            and
            abs(s5 - s20)
            /
            c_close
            <
            0.03
        )
    )


    # ========================================================
    # ③ 線密集
    # ========================================================

    ma_range = (
        max(s5, s20, s60)
        -
        min(s5, s20, s60)
    )

    is_dense = (

        (
            ma_range
            /
            c_close
        )
        <
        0.035

        and
        c_close > s5
    )


    # ========================================================
    # ④ PPP
    # ========================================================

    is_ppp = (
        s5
        >
        s20
        >
        s60
        >
        s100
    )


    # ========================================================
    # スコア
    # ========================================================

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

    jst = pytz.timezone(
        "Asia/Tokyo"
    )

    now_jst = datetime.now(
        jst
    )

    updated_str = (
        now_jst
        .strftime("%m/%d %H:%M")
    )

    print(
        f">>> スクリーニング開始: "
        f"{updated_str}"
    )

    print(
        f">>> 監視ユニバース: "
        f"{len(TICKERS)}銘柄"
    )


    # ========================================================
    # 株価一括取得
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

    latest_signal_dates = []

    box_observations = {}


    # ========================================================
    # 80銘柄すべて処理
    # ========================================================

    for ticker in TICKERS:

        try:

            # ------------------------------------------------
            # データ抽出
            # ------------------------------------------------

            df = extract_ticker_frame(
                downloaded,
                ticker
            )

            if df.empty:

                skipped.append({
                    "ticker":
                        ticker,

                    "reason":
                        "データ取得失敗",
                })

                continue


            # ------------------------------------------------
            # 未確定当日足除外
            # ------------------------------------------------

            df = keep_confirmed_daily_bars(
                df,
                now_jst
            )

            # 欠損行を落とす前に観察値を計算し、欠損を隠さない。
            box_observations[clean_code(ticker)] = calculate_box_metrics(df)


            # ------------------------------------------------
            # 欠損除去
            # ------------------------------------------------

            df = df.dropna(
                subset=[
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Volume",
                ]
            ).copy()

            df = df.sort_index()


            if len(df) < 60:

                skipped.append({
                    "ticker":
                        ticker,

                    "reason":
                        f"履歴不足({len(df)}行)",
                })

                continue


            # ------------------------------------------------
            # 最新足
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
            # 異常値チェック
            # ------------------------------------------------

            if not all(
                np.isfinite(v)
                and v > 0

                for v in [
                    close,
                    open_p,
                ]
            ):

                skipped.append({
                    "ticker":
                        ticker,

                    "reason":
                        "価格データ異常",
                })

                continue


            if (
                not np.isfinite(volume)
                or volume < 0
            ):

                skipped.append({
                    "ticker":
                        ticker,

                    "reason":
                        "出来高データ異常",
                })

                continue


            closes = df["Close"]


            # ------------------------------------------------
            # SMA50
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
            # 20日平均出来高
            # ------------------------------------------------

            vol20 = calc_vol20(df)


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
            # 前日まで250営業日高値
            # ------------------------------------------------

            prior_high250 = (
                calculate_prior_250_high(
                    df
                )
            )


            # ------------------------------------------------
            # 高値乖離
            # ------------------------------------------------

            off_high = calc_off_high(
                close,
                prior_high250
            )


            # ------------------------------------------------
            # 5日平均売買代金
            # ------------------------------------------------

            avg_turnover_5d = (
                calc_avg_turnover_5d(
                    df
                )
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
            # 基本情報
            # ------------------------------------------------

            code = clean_code(
                ticker
            )

            name = get_name(
                ticker
            )

            fund_score = (
                FUND_SCORES.get(
                    ticker
                )
            )

            signal_date = (
                pd.Timestamp(
                    df.index[-1]
                )
                .strftime("%Y-%m-%d")
            )

            latest_signal_dates.append(
                signal_date
            )


            # =================================================
            # A. PF4.11入口条件
            #
            # 流動性条件は後付けしない
            # =================================================

            if matches_pf411_prebreakout(

                off_high=off_high,

                close=close,

                sma50=sma50,

                volume=volume,

                vol20=vol20,

                history_rows=len(df),

            ):

                pf411_candidates.append({

                    "code":
                        code,

                    "name":
                        name,

                    "price":
                        int(
                            round(close)
                        ),

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
                        (
                            int(
                                round(
                                    avg_turnover_5d
                                )
                            )
                            if
                            np.isfinite(
                                avg_turnover_5d
                            )
                            else
                            None
                        ),

                    "fund_score":
                        fund_score,

                    "signal_date":
                        signal_date,

                    "signal_conditions":
                        (
                            "-3.0%<=off_high<0%, "
                            "close>SMA50, "
                            "volume>=VolSMA20*1.2"
                        ),
                })


            # =================================================
            # 250日高値取得不能
            # =================================================

            if off_high is None:

                skipped.append({
                    "ticker":
                        ticker,

                    "reason":
                        (
                            "前日までの250営業日高値"
                            "を計算不能"
                        ),
                })

                continue


            # =================================================
            # B. 相場流
            # =================================================

            soba_score, soba_pattern = (
                evaluate_soba_pattern(
                    df
                )
            )


            tech_nh_score = (
                evaluate_technical_new_high(

                    close=close,

                    sma50=sma50,

                    off_high=off_high,

                    volume=volume,

                    vol20=vol20,
                )
            )


            # 相場流は従来通り
            # +3%超は過熱として除外
            if (
                off_high
                <=
                LAUNCHPAD_MAX_OFF_HIGH
            ):

                if (
                    not
                    APPLY_TURNOVER_FILTER_TO_ACTIVE_CANDIDATES

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
                                int(
                                    round(close)
                                ),

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
            # C. 新高値ボード
            #
            # 発射台・ブレイク：
            #   流動性条件あり
            #
            # 95点見送り：
            #   流動性条件なし
            #   50MA上なら全件観察
            # =================================================

            launch_score, launch_status = (
                evaluate_launchpad(

                    close=close,

                    sma50=sma50,

                    off_high=off_high,

                    volume=volume,

                    vol20=vol20,
                )
            )


            # -------------------------------------------------
            # C-1 発射台 / ブレイク確認
            #
            # 実売買候補なので流動性確認
            # -------------------------------------------------

            if launch_status in (
                "★発射台",
                "★ブレイク確認",
            ):

                if (
                    not
                    APPLY_TURNOVER_FILTER_TO_ACTIVE_CANDIDATES

                    or

                    liquidity_ok
                ):

                    new_high_candidates.append({

                        "code":
                            code,

                        "name":
                            name,

                        "price":
                            int(
                                round(close)
                            ),

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
                            (
                                int(
                                    round(
                                        avg_turnover_5d
                                    )
                                )
                                if
                                np.isfinite(
                                    avg_turnover_5d
                                )
                                else
                                None
                            ),

                        "sma50":
                            round(
                                sma50,
                                2
                            ),

                        "signal_date":
                            signal_date,
                    })


            # -------------------------------------------------
            # C-2 +3%超 見送り
            #
            # 観察用。
            # 流動性フィルターをかけない。
            #
            # evaluate_launchpad()内で
            # close > SMA50 は確認済み。
            # -------------------------------------------------

            elif launch_status == "見送り":

                new_high_candidates.append({

                    "code":
                        code,

                    "name":
                        name,

                    "price":
                        int(
                            round(close)
                        ),

                    "nh_score":
                        95,

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
                        "見送り",

                    "avg_turnover_5d":
                        (
                            int(
                                round(
                                    avg_turnover_5d
                                )
                            )
                            if
                            np.isfinite(
                                avg_turnover_5d
                            )
                            else
                            None
                        ),

                    "sma50":
                        round(
                            sma50,
                            2
                        ),

                    "signal_date":
                        signal_date,
                })


        except Exception as e:

            skipped.append({

                "ticker":
                    ticker,

                "reason":
                    f"例外: {e}",
            })

            print(
                f"エラー発生 "
                f"({ticker}): {e}"
            )


    # ========================================================
    # ランキング
    #
    # 85/90点売買候補を上
    # 95点見送りはその下
    #
    # ※95という数字だけで上位にしない
    # ========================================================

    STATUS_PRIORITY = {

        "★ブレイク確認": 2,

        "★発射台": 2,

        "見送り": 1,
    }


    new_high_candidates.sort(

        key=lambda x: (

            STATUS_PRIORITY.get(
                x["status"],
                0
            ),

            x["nh_score"],

            -abs(
                x["off_high"]
            ),

            x["vol_ratio"],
        ),

        reverse=True,
    )


    # ========================================================
    # 相場流ランキング
    # ========================================================

    soba_candidates.sort(

        key=lambda x: (

            x["total_score"],

            x["soba_score"],

            x["nh_score"],
        ),

        reverse=True,
    )


    # ========================================================
    # PF4.11ランキング
    # ========================================================

    pf411_candidates.sort(

        key=lambda x: (

            x["off_high"],

            x["vol_ratio"],
        ),

        reverse=True,
    )


    # ========================================================
    # 集計
    # ========================================================

    confirmed_fund_count = sum(

        1

        for ticker in TICKERS

        if
        FUND_SCORES.get(
            ticker
        )
        is not None
    )


    data_date = (

        max(
            latest_signal_dates
        )

        if latest_signal_dates

        else None
    )


    active_count = sum(

        1

        for x in new_high_candidates

        if x["status"] in (
            "★発射台",
            "★ブレイク確認",
        )
    )


    watch_count = sum(

        1

        for x in new_high_candidates

        if
        x["status"]
        ==
        "見送り"
    )


    # ========================================================
    # JSON
    #
    # 全件保存
    # ========================================================

    # 既存の判定・ソート完了後に付加するため、順位は変わらない。
    for candidates in (new_high_candidates, soba_candidates, pf411_candidates):
        for candidate in candidates:
            candidate["box"] = box_observations.get(candidate["code"])

    output_data = {

        "box_observations": box_observations,
        "box_reference": {
            "version": 1,
            "observation_only": True,
            "min_bars": BOX_MIN_BARS,
            "max_bars": BOX_MAX_BARS,
            "max_width_pct": BOX_MAX_WIDTH_PCT,
            "recent_bars": BOX_RECENT_BARS,
            "basis": "最新判定足を除く過去の確定日足。高値・安値を使用。",
            "duration_definition": "末尾から遡り幅15%以内に収まる最長10〜60本。暫定的な近似。",
            "width_definition": "(期間高値-期間安値)/期間高値*100",
            "contraction_definition": "直近5本の幅%/その前5本の幅%。1未満は縮小。",
            "limitations": (
                "ダーバス型の認定や上昇予測ではない。緩やかなトレンドも含み得る。"
                "60本の場合は上限打切り。比較元ゼロ幅は比率null。"
                "取引所カレンダーによる欠落日・データ鮮度は検証しない。"
                "ランキング、売買条件、PF4.11入口条件には使用しない。"
            ),
        },

        "updated_at":
            updated_str,


        "data_date":
            data_date,


        # ----------------------------------------------------
        # データ仕様
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
                ),

            "volume_reference":
                (
                    "PF4.11互換のため"
                    "20日平均出来高は"
                    "最新足を含むrolling(20)"
                ),
        },


        # ----------------------------------------------------
        # ユニバース
        # ----------------------------------------------------

        "universe": {

            "ticker_count":
                len(TICKERS),

            "launchpad_screened_count":
                len(TICKERS),

            "confirmed_fund_score_count":
                confirmed_fund_count,

            "fund_score_policy":
                (
                    "fund_scoreは参考表示。"
                    "未登録銘柄も発射台判定対象。"
                ),
        },


        # ----------------------------------------------------
        # 件数
        # ----------------------------------------------------

        "counts": {

            "active_new_high_count":
                active_count,

            "watch_overheated_count":
                watch_count,

            "total_new_high_display_count":
                len(
                    new_high_candidates
                ),

            "soba_count":
                len(
                    soba_candidates
                ),

            "pf411_count":
                len(
                    pf411_candidates
                ),
        },


        # ----------------------------------------------------
        # 発射台 + ブレイク + 見送り
        #
        # 全件
        # ----------------------------------------------------

        "new_high_ranks":
            new_high_candidates,


        # ----------------------------------------------------
        # 相場流
        #
        # 全件
        # ----------------------------------------------------

        "soba_ranks":
            soba_candidates,


        # ----------------------------------------------------
        # PF4.11
        #
        # 全件
        # ----------------------------------------------------

        "pf411_ranks":
            pf411_candidates,


        # ----------------------------------------------------
        # 新高値説明
        # ----------------------------------------------------

        "new_high_reference": {

            "label":
                (
                    "新高値発射台/"
                    "ブレイク確認/"
                    "過熱見送り"
                ),

            "conditions": [

                "監視80銘柄すべてを判定",

                "終値 > SMA50",

                (
                    "-6.0% <= off_high <= 0% "
                    "は発射台"
                ),

                (
                    "0% < off_high <= +3.0% "
                    "はブレイク確認"
                ),

                (
                    "+3.0%超は"
                    "過熱見送りとして観察表示"
                ),

                (
                    "発射台・ブレイク確認には"
                    f"5日平均売買代金 >= "
                    f"{MIN_AVG_TURNOVER:,}円"
                ),

                (
                    "見送りには"
                    "売買代金フィルターを適用しない"
                ),
            ],

            "fund_score_note":
                (
                    "fund_scoreは現時点では"
                    "参考表示のみ。"
                    "未登録銘柄を除外しない。"
                ),

            "score_note":
                (
                    "85=通常条件、"
                    "90=出来高1.2倍超、"
                    "95=+3%超の過熱見送り。"
                    "95は85/90より良い"
                    "という意味ではない。"
                ),
        },


        # ----------------------------------------------------
        # PF4.11説明
        # ----------------------------------------------------

        "pf411_reference": {

            "label":
                (
                    "PF4.11過去バックテストの"
                    "入口条件に対応する候補。"
                    "PF4.11自体を"
                    "再計算したものではない。"
                ),

            "conditions": [

                "-3.0% <= off_high < 0.0%",

                "終値 > SMA50",

                (
                    "当日出来高 >= "
                    "20日平均出来高 * 1.2"
                ),

                "過去データ260行以上",
            ],

            "execution_note":
                (
                    "過去PF4.11の完全再現には、"
                    "翌営業日始値エントリー、"
                    "出口、保有期間、"
                    "同時シグナル時の優先順位、"
                    "資金配分などの一致が必要。"
                ),

            "limitations":
                (
                    "fund_score・PBR・"
                    "売買代金条件は"
                    "PF4.11入口条件へ"
                    "後付けしない。"
                ),
        },


        # ----------------------------------------------------
        # スキップログ
        # ----------------------------------------------------

        "skipped":
            skipped,
    }


    # ========================================================
    # JSON保存
    # ========================================================

    with open(
        "stocks_data.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output_data,
            f,
            ensure_ascii=False,
            indent=2,
        )


    # ========================================================
    # ログ
    # ========================================================

    print(
        ">>> 完了: stocks_data.json生成 "
        f"| 母集団={len(TICKERS)} "
        f"| 発射台/ブレイク={active_count} "
        f"| 見送り95={watch_count} "
        f"| 新高値表示合計={len(new_high_candidates)} "
        f"| 相場流={len(soba_candidates)} "
        f"| PF4.11入口={len(pf411_candidates)} "
        f"| fund_score登録={confirmed_fund_count} "
        f"| スキップ={len(skipped)} "
        f"| データ日={data_date}"
    )


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    analyze_market()
