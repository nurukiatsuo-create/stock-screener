// ============================================================
// 【新高値 × 相場流 × PF4.11】自動連携ダッシュボード
//
// Widget Parameter
//   空欄    : 新高値 発射台ボード
//   soba    : 相場流 × 新高値
//   pf411   : PF4.11入口条件候補
//
// 方針
// ・GitHub側で抽出された候補を全件表示
// ・件数に応じて文字サイズ・行間を自動調整
// ・Scriptable側では再スクリーニングしない
// ・fund_score未登録は「—」表示
// ・銘柄タップでTradingView日足を開く
// ============================================================


// ============================================================
// 1. GitHub設定
// ============================================================

const GITHUB_USER = "nurukiatsuo-create";
const REPO_NAME = "stock-screener";
const BRANCH = "main";

const RAW_URL =
  `https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/${BRANCH}/stocks_data.json?t=${Date.now()}`;


// ============================================================
// 2. 銘柄コード → 日本語社名
// ============================================================

const NAMES = {

  "7826": "フルヤ金属",
  "6912": "菊水HD",
  "9249": "日本エコ",
  "7192": "日モーゲージ",

  "6727": "ワコム",
  "6364": "北越工業",
  "3560": "ほぼ日",
  "5957": "日東精工",

  "7172": "JIA",
  "1401": "エムビーエス",
  "6652": "IDEC",
  "6345": "アイチコーポ",

  "6862": "ミナトHD",
  "6855": "日電子材料",
  "6407": "CKD",
  "6134": "FUJI",

  "6629": "テクノホライ",
  "6226": "守谷輸送機",
  "6904": "原田工業",
  "6368": "オルガノ",

  "6941": "山一電機",
  "6946": "日アビオ",
  "6866": "日置電機",
  "7254": "ユニバンス",

  "6258": "平田機工",
  "6518": "三相電機",
  "6616": "トレックス",
  "6677": "SKエレク",

  "6474": "不二越",
  "6327": "北川精機",
  "7715": "長野計器",
  "6508": "明電舎",

  "4776": "サイボウズ",
  "3923": "ラクス",
  "6027": "弁護士ドット",
  "3663": "セルシス",

  "3968": "セグエ",
  "5033": "ヌーラボ",
  "4055": "T&S",
  "5254": "Arent",

  "4828": "Bエンジニア",
  "4825": "ウェザーニュー",
  "4258": "網屋",
  "3692": "FFRI",

  "4012": "アクシス",
  "3763": "プロシップ",
  "7094": "NexTone",
  "3696": "セレス",

  "3040": "ソリトン",
  "4440": "ヴィッツ",
  "4371": "C＆C",
  "4414": "フレクト",

  "4396": "システムサポ",
  "5591": "AVILEN",
  "6998": "日タングステン",
  "6871": "日マイクロ",

  "6787": "メイコー",
  "4368": "扶桑化学",
  "4369": "トリケミカル",
  "4975": "JCU",

  "4626": "太陽HD",
  "4971": "メック",
  "4046": "大阪ソーダ",
  "3441": "サンコーテクノ",

  "3449": "テクノフレ",
  "4970": "東洋合成",
  "5805": "SWCC",
  "7609": "ダイトロン",

  "4461": "第一工薬",
  "7781": "平山HD",
  "5018": "MORESCO",
  "4100": "戸田工業",

  "3482": "ロードスター",
  "3498": "霞ヶ関キャピ",
  "7148": "FPG",
  "2884": "ヨシムラFD",

  "5136": "tripla",
  "7372": "デコルテHD",
  "5589": "オートサーバ",
  "4765": "SBIGアセット"
};


// ============================================================
// 3. Parameter判定
// ============================================================

const param =
  (args.widgetParameter || "")
    .trim()
    .toLowerCase();

const isSoba =
  param === "soba" ||
  param === "相場";

const isPF411 =
  param === "pf411" ||
  param === "pf4.11" ||
  param === "411";


// ============================================================
// 4. Widget基本設定
// ============================================================

const widget = new ListWidget();

widget.backgroundColor =
  new Color("#161d26");

widget.setPadding(
  10,
  8,
  10,
  8
);


// ============================================================
// 5. GitHub JSON取得
// ============================================================

let data = null;

try {

  const req =
    new Request(RAW_URL);

  req.timeoutInterval = 15;

  data =
    await req.loadJSON();

} catch (e) {

  console.error(e);

}


// ============================================================
// 6. JSON取得失敗
// ============================================================

if (!data) {

  const err =
    widget.addText(
      "⚠️ データ取得失敗\nGitHubまたは通信環境を確認してください"
    );

  err.font =
    Font.boldSystemFont(13);

  err.textColor =
    Color.red();

  Script.setWidget(widget);
  Script.complete();

} else {


// ============================================================
// 7. 表示データ
//
// ★ slice()を使わない
// ★ 条件合致銘柄を全件表示
// ============================================================

let items = [];

if (isSoba) {

  items =
    data.soba_ranks || [];

} else if (isPF411) {

  items =
    data.pf411_ranks || [];

} else {

  items =
    data.new_high_ranks || [];

}

const itemCount =
  items.length;


// ============================================================
// 8. 件数に応じた自動レイアウト
// ============================================================

let mainFontSize;
let codeFontSize;
let signalFontSize;
let rowSpacing;
let headerFontSize;
let columnFontSize;
let sectionSpacing;


// 1～7銘柄
if (itemCount <= 7) {

  mainFontSize = 13.5;
  codeFontSize = 9.5;
  signalFontSize = 11.0;
  rowSpacing = 6.0;
  headerFontSize = 14.0;
  columnFontSize = 10.5;
  sectionSpacing = 5.0;

}

// 8～10銘柄
else if (itemCount <= 10) {

  mainFontSize = 12.5;
  codeFontSize = 9.0;
  signalFontSize = 10.2;
  rowSpacing = 4.0;
  headerFontSize = 14.0;
  columnFontSize = 10.0;
  sectionSpacing = 4.0;

}

// 11～13銘柄
else if (itemCount <= 13) {

  mainFontSize = 11.5;
  codeFontSize = 8.5;
  signalFontSize = 9.4;
  rowSpacing = 2.5;
  headerFontSize = 13.5;
  columnFontSize = 9.5;
  sectionSpacing = 3.5;

}

// 14～16銘柄
else if (itemCount <= 16) {

  mainFontSize = 10.4;
  codeFontSize = 8.0;
  signalFontSize = 8.6;
  rowSpacing = 1.5;
  headerFontSize = 13.0;
  columnFontSize = 9.0;
  sectionSpacing = 3.0;

}

// 17～20銘柄
else if (itemCount <= 20) {

  mainFontSize = 9.4;
  codeFontSize = 7.4;
  signalFontSize = 7.8;
  rowSpacing = 0.8;
  headerFontSize = 12.2;
  columnFontSize = 8.3;
  sectionSpacing = 2.0;

}

// 21～24銘柄
else if (itemCount <= 24) {

  mainFontSize = 8.5;
  codeFontSize = 6.8;
  signalFontSize = 7.0;
  rowSpacing = 0.2;
  headerFontSize = 11.5;
  columnFontSize = 7.8;
  sectionSpacing = 1.5;

}

// 25～30銘柄
else if (itemCount <= 30) {

  mainFontSize = 7.6;
  codeFontSize = 6.1;
  signalFontSize = 6.4;
  rowSpacing = 0;
  headerFontSize = 10.5;
  columnFontSize = 7.0;
  sectionSpacing = 1.0;

}

// 31銘柄以上
else {

  mainFontSize = 6.8;
  codeFontSize = 5.6;
  signalFontSize = 5.8;
  rowSpacing = 0;
  headerFontSize = 9.5;
  columnFontSize = 6.3;
  sectionSpacing = 0.5;

}


// ============================================================
// 9. タイトル
// ============================================================

const header =
  widget.addStack();

header.layoutHorizontally();


let titleText = "";
let titleColor = null;


if (isSoba) {

  titleText =
    `【相場流×新高値】${itemCount}銘柄`;

  titleColor =
    new Color("#5ac8fa");

}

else if (isPF411) {

  titleText =
    `【PF4.11条件】${itemCount}銘柄`;

  titleColor =
    new Color("#ff9f0a");

}

else {

  titleText =
    `【新高値】発射台 ${itemCount}銘柄`;

  titleColor =
    new Color("#ffd60a");

}


const title =
  header.addText(titleText);

title.font =
  Font.boldSystemFont(
    headerFontSize
  );

title.textColor =
  titleColor;

title.lineLimit = 1;


header.addSpacer();


const updated =
  header.addText(
    `[${data.updated_at || ""}]`
  );

updated.font =
  Font.systemFont(
    Math.max(
      headerFontSize - 3,
      6
    )
  );

updated.textColor =
  new Color("#8e8e93");

updated.lineLimit = 1;


widget.addSpacer(
  sectionSpacing
);


// ============================================================
// 10. カラム見出し
// ============================================================

const cols =
  widget.addStack();

cols.layoutHorizontally();


const firstCol =
  cols.addText(
    "銘柄 (日足)"
  );

firstCol.font =
  Font.systemFont(
    columnFontSize
  );

firstCol.textColor =
  new Color("#8e8e93");

firstCol.lineLimit = 1;


cols.addSpacer();


let colDef = [];


if (isSoba) {

  colDef = [

    {
      title: "現在値",
      width: 54
    },

    {
      title: "相場",
      width: 30
    },

    {
      title: "新高",
      width: 30
    },

    {
      title: "技/シグナル",
      width: 68
    }

  ];

}

else if (isPF411) {

  colDef = [

    {
      title: "現在値",
      width: 56
    },

    {
      title: "高値差",
      width: 46
    },

    {
      title: "出来高",
      width: 48
    },

    {
      title: "50MA",
      width: 52
    }

  ];

}

else {

  colDef = [

    {
      title: "現在値",
      width: 56
    },

    {
      title: "テク",
      width: 34
    },

    {
      title: "業績",
      width: 34
    },

    {
      title: "高値差",
      width: 48
    }

  ];

}


for (
  let i = 0;
  i < colDef.length;
  i++
) {

  const c =
    colDef[i];

  const stack =
    cols.addStack();

  stack.size =
    new Size(
      c.width,
      0
    );

  stack.addSpacer();


  const text =
    stack.addText(
      c.title
    );

  text.font =
    Font.systemFont(
      columnFontSize
    );

  text.textColor =
    new Color("#8e8e93");

  text.lineLimit = 1;


  if (
    i < colDef.length - 1
  ) {

    cols.addSpacer(4);

  }

}


widget.addSpacer(
  sectionSpacing
);


// ============================================================
// 11. 候補なし
// ============================================================

if (itemCount === 0) {

  widget.addSpacer(12);


  let message = "";

  if (isSoba) {

    message =
      "現在、相場流条件に該当する銘柄はありません";

  }

  else if (isPF411) {

    message =
      "現在、PF4.11入口条件に該当する銘柄はありません";

  }

  else {

    message =
      "現在、発射台条件に該当する銘柄はありません";

  }


  const empty =
    widget.addText(message);

  empty.font =
    Font.boldSystemFont(13);

  empty.textColor =
    new Color("#8e8e93");

  empty.centerAlignText();


} else {


// ============================================================
// 12. 全銘柄描画
// ============================================================

for (
  let i = 0;
  i < items.length;
  i++
) {

  const item =
    items[i];


  const row =
    widget.addStack();

  row.layoutHorizontally();


  // ----------------------------------------------------------
  // コード・社名
  // ----------------------------------------------------------

  const rawCode =
    String(
      item.code || ""
    )
      .replace(
        ".T",
        ""
      );


  const codeNum =
    rawCode ||
    String(
      item.name || ""
    );


  const companyName =
    NAMES[codeNum] ||
    item.name ||
    codeNum;


  // TradingView日足
  row.url =
    `https://jp.tradingview.com/chart/?symbol=TSE%3A${codeNum}&interval=D`;


  // ----------------------------------------------------------
  // 左：順位・コード
  // ----------------------------------------------------------

  const nameStack =
    row.addStack();

  nameStack.layoutHorizontally();


  const codeStack =
    nameStack.addStack();

  codeStack.size =
    new Size(
      itemCount >= 17
        ? 39
        : 46,
      0
    );


  const codeText =
    codeStack.addText(
      `${i + 1}.${codeNum}`
    );

  codeText.font =
    Font.systemFont(
      codeFontSize
    );

  codeText.textColor =
    new Color("#8e8e93");

  codeText.lineLimit = 1;


  nameStack.addSpacer(2);


  // ----------------------------------------------------------
  // 社名
  // ----------------------------------------------------------

  const nameText =
    nameStack.addText(
      companyName
    );

  nameText.font =
    Font.boldSystemFont(
      mainFontSize
    );

  nameText.textColor =
    Color.white();

  nameText.lineLimit = 1;


  row.addSpacer();


  // ----------------------------------------------------------
  // 現在値
  // ----------------------------------------------------------

  const priceStack =
    row.addStack();

  priceStack.size =
    new Size(
      isSoba
        ? 54
        : 56,
      0
    );

  priceStack.addSpacer();


  const price =
    Number(
      item.price
    );


  const priceString =
    Number.isFinite(price)
      ? price.toLocaleString()
      : "-";


  const priceText =
    priceStack.addText(
      priceString
    );

  priceText.font =
    Font.boldSystemFont(
      mainFontSize
    );

  priceText.textColor =
    Color.white();

  priceText.lineLimit = 1;


  row.addSpacer(4);


// ============================================================
// 13-A. 相場流モード
// ============================================================

  if (isSoba) {

    // 相場スコア

    const sobaStack =
      row.addStack();

    sobaStack.size =
      new Size(
        30,
        0
      );

    sobaStack.addSpacer();


    const sobaScore =
      Number(
        item.soba_score
      );


    const sobaText =
      sobaStack.addText(
        Number.isFinite(
          sobaScore
        )
          ? String(sobaScore)
          : "-"
      );


    sobaText.font =
      Font.boldSystemFont(
        mainFontSize
      );


    if (
      sobaScore >= 90
    ) {

      sobaText.textColor =
        new Color("#ff453a");

    }

    else if (
      sobaScore >= 80
    ) {

      sobaText.textColor =
        new Color("#ffd60a");

    }

    else {

      sobaText.textColor =
        Color.white();

    }


    sobaText.lineLimit = 1;


    row.addSpacer(4);


    // 新高値スコア

    const nhStack =
      row.addStack();

    nhStack.size =
      new Size(
        30,
        0
      );

    nhStack.addSpacer();


    const nhScore =
      Number(
        item.nh_score
      );


    const nhText =
      nhStack.addText(
        Number.isFinite(
          nhScore
        )
          ? String(nhScore)
          : "-"
      );


    nhText.font =
      Font.systemFont(
        mainFontSize
      );

    nhText.textColor =
      new Color("#8e8e93");

    nhText.lineLimit = 1;


    row.addSpacer(4);


    // 技・シグナル

    const signalStack =
      row.addStack();

    signalStack.size =
      new Size(
        68,
        0
      );

    signalStack.addSpacer();


    const signal =
      item.soba_pattern ||
      "";


    const signalText =
      signalStack.addText(
        signal
      );

    signalText.font =
      Font.boldSystemFont(
        signalFontSize
      );


    if (
      signal.includes("★")
    ) {

      signalText.textColor =
        new Color("#ff453a");

    }

    else if (
      signal.includes("PPP")
    ) {

      signalText.textColor =
        new Color("#30d158");

    }

    else {

      signalText.textColor =
        new Color("#5ac8fa");

    }


    signalText.lineLimit = 1;

  }


// ============================================================
// 13-B. PF4.11モード
// ============================================================

  else if (isPF411) {

    // 高値差

    const diffStack =
      row.addStack();

    diffStack.size =
      new Size(
        46,
        0
      );

    diffStack.addSpacer();


    const offHigh =
      Number(
        item.off_high
      );


    let diffString =
      "-";


    if (
      Number.isFinite(
        offHigh
      )
    ) {

      diffString =
        offHigh >= 0
          ? `+${offHigh}`
          : String(offHigh);

    }


    const diffText =
      diffStack.addText(
        diffString
      );

    diffText.font =
      Font.boldSystemFont(
        mainFontSize
      );

    diffText.textColor =
      new Color("#30d158");

    diffText.lineLimit = 1;


    row.addSpacer(4);


    // 出来高倍率

    const volumeStack =
      row.addStack();

    volumeStack.size =
      new Size(
        48,
        0
      );

    volumeStack.addSpacer();


    const volumeRatio =
      Number(
        item.vol_ratio
      );


    const volumeString =
      Number.isFinite(
        volumeRatio
      )
        ? `${volumeRatio.toFixed(2)}x`
        : "-";


    const volumeText =
      volumeStack.addText(
        volumeString
      );

    volumeText.font =
      Font.boldSystemFont(
        signalFontSize
      );


    if (
      volumeRatio >= 1.5
    ) {

      volumeText.textColor =
        new Color("#ff453a");

    }

    else {

      volumeText.textColor =
        new Color("#ffd60a");

    }


    volumeText.lineLimit = 1;


    row.addSpacer(4);


    // 50MA

    const maStack =
      row.addStack();

    maStack.size =
      new Size(
        52,
        0
      );

    maStack.addSpacer();


    const sma50 =
      Number(
        item.sma50
      );


    const maString =
      Number.isFinite(
        sma50
      )
        ? Math.round(
            sma50
          ).toLocaleString()
        : "-";


    const maText =
      maStack.addText(
        maString
      );

    maText.font =
      Font.systemFont(
        signalFontSize
      );

    maText.textColor =
      new Color("#8e8e93");

    maText.lineLimit = 1;

  }


// ============================================================
// 13-C. 新高値発射台モード
// ============================================================

  else {

    // テクニカル点

    const techStack =
      row.addStack();

    techStack.size =
      new Size(
        34,
        0
      );

    techStack.addSpacer();


    const nhScore =
      Number(
        item.nh_score
      );


    const techText =
      techStack.addText(
        Number.isFinite(
          nhScore
        )
          ? String(nhScore)
          : "-"
      );


    techText.font =
      Font.boldSystemFont(
        mainFontSize
      );

    techText.textColor =
      new Color("#ffd60a");

    techText.lineLimit = 1;


    row.addSpacer(4);


    // --------------------------------------------------------
    // fund_score
    //
    // 未登録なら —
    // 未登録でも候補から除外しない
    // --------------------------------------------------------

    const fundStack =
      row.addStack();

    fundStack.size =
      new Size(
        34,
        0
      );

    fundStack.addSpacer();


    const rawFund =
      item.fund_score;


    const fundScore =
      Number(
        rawFund
      );


    const hasFund =
      rawFund !== null &&
      rawFund !== undefined &&
      rawFund !== "" &&
      Number.isFinite(
        fundScore
      );


    const isPerfect =
      hasFund &&
      fundScore === 100;


    let fundString =
      "—";


    if (hasFund) {

      fundString =
        isPerfect
          ? "💯"
          : String(
              fundScore
            );

    }


    const fundText =
      fundStack.addText(
        fundString
      );


    if (isPerfect) {

      fundText.font =
        Font.systemFont(
          Math.max(
            signalFontSize,
            7
          )
        );

    }

    else {

      fundText.font =
        Font.boldSystemFont(
          mainFontSize
        );

    }


    fundText.textColor =
      hasFund
        ? Color.white()
        : new Color("#8e8e93");


    fundText.lineLimit = 1;


    row.addSpacer(4);


    // 高値差

    const diffStack =
      row.addStack();

    diffStack.size =
      new Size(
        48,
        0
      );

    diffStack.addSpacer();


    const offHigh =
      Number(
        item.off_high
      );


    let diffString =
      "-";


    if (
      Number.isFinite(
        offHigh
      )
    ) {

      diffString =
        offHigh >= 0
          ? `+${offHigh}`
          : String(offHigh);

    }


    const diffText =
      diffStack.addText(
        diffString
      );

    diffText.font =
      Font.boldSystemFont(
        mainFontSize
      );


    // 0%以上 = ブレイク後 → 黄
    // 0%未満 = 発射台 → 緑

    if (
      Number.isFinite(offHigh) &&
      offHigh > 0
    ) {

      diffText.textColor =
        new Color("#ffd60a");

    }

    else {

      diffText.textColor =
        new Color("#30d158");

    }


    diffText.lineLimit = 1;

  }


// ============================================================
// 14. 行間
// ============================================================

  if (
    rowSpacing > 0
  ) {

    widget.addSpacer(
      rowSpacing
    );

  }

}

}


// ============================================================
// 15. 下余白
// ============================================================

widget.addSpacer();


// ============================================================
// 16. Widgetセット
// ============================================================

Script.setWidget(widget);
Script.complete();

}
