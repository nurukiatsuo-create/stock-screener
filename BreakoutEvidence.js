// Scriptable: add as a NEW script. Parameter: close / intraday / holding / failed
// This board requires scan.py with breakout_board. No trading orders are sent.
const groups = {
  close: ["close_breaks", "当日・終値突破"],
  intraday: ["intraday_rejections", "日中突破・終値未維持"],
  holding: ["holding_prior_breaks", "過去の突破水準を維持"],
  failed: ["failed_prior_breaks", "直近突破後に終値割れ"]
};
const mode = groups[(args.widgetParameter || "close").trim()] || groups.close;
const req = new Request("https://raw.githubusercontent.com/nurukiatsuo-create/stock-screener/main/stocks_data.json?t=" + Date.now());
const widget = new ListWidget();
widget.backgroundColor = new Color("#161d26");
widget.setPadding(10, 10, 10, 10);
function line(value, color = "#ffffff", size = 12) {
  const text = widget.addText(value);
  text.textColor = new Color(color);
  text.font = Font.systemFont(size);
  return text;
}
function num(value, digits = 2) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}
try {
  const data = await req.loadJSON();
  line(mode[1], "#ffd60a", 14);
  line("日足 " + (data.data_date || "不明") + "／更新 " + (data.updated_at || "不明"), "#a9b4c2", 10);
  widget.addSpacer(5);
  if (!data.breakout_board) {
    line("新判定データ未生成", "#ff9f0a");
  } else {
    const rows = data.breakout_board[mode[0]] || [];
    line("該当 " + rows.length + "件・コード順／買い推奨順ではない", "#a9b4c2", 9);
    for (const row of rows.slice(0, 5)) {
      const e = row.evidence, t = e.today;
      widget.addSpacer(5);
      line(row.code + " " + row.name + "  " + num(t.close, 0));
      line("出来高 " + num(t.volume_ratio_prior20) + "倍／上ヒゲ " + num(t.upper_wick_fraction === null ? null : t.upper_wick_fraction * 100, 0) + "%", "#a9b4c2", 10);
      const event = mode[0] === "holding_prior_breaks" ? e.prior_surviving_event : e.latest_event;
      if (event) line(event.date + "基準 " + num(event.reference_high, 0) + "／維持 " + event.maintained_bars + "本", "#a9b4c2", 9);
    }
    if (!rows.length) line("該当なし。件数を埋めるための補充はしません。", "#a9b4c2", 10);
    if (rows.length > 5) line("ほか " + (rows.length - 5) + "件", "#a9b4c2", 10);
    line("取得・日付確認待ち " + (data.breakout_board.unavailable || []).length + "件", "#ff9f0a", 9);
  }
  widget.addSpacer(5);
  line("ボックス未認定・将来のダマシ排除を保証しない", "#a9b4c2", 9);
} catch (error) {
  line("取得失敗：以前の値を最新として表示しません", "#ff9f0a", 11);
}
Script.setWidget(widget);
if (!config.runsInWidget) await widget.presentLarge();
Script.complete();
