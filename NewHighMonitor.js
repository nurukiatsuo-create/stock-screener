// Scriptable: widget parameter candidates (default), watch, holdings.
// Uses confirmed daily data. No orders. Budget previews are NOT recommended sizes.
const mode = (args.widgetParameter || 'candidates').trim();
const w = new ListWidget(); w.backgroundColor = new Color('#161d26'); w.setPadding(12,12,12,12);
function line(s,color='#ffffff',size=11){const t=w.addText(s);t.textColor=new Color(color);t.font=Font.systemFont(size);}
function n(x,d=0){return Number.isFinite(x)?x.toLocaleString('ja-JP',{maximumFractionDigits:d}):'—';}
try {
 const req=new Request('https://raw.githubusercontent.com/nurukiatsuo-create/stock-screener/main/stocks_data.json?t='+Date.now());
 req.timeoutInterval=20;
 const data=await req.loadJSON(), s=data.strategy;
 line('新高値・ボックス監視','#ffd60a',16);
 line('日足 '+(data.data_date||'不明')+'／更新 '+(data.updated_at||'不明'),'#a9b4c2',9);
 if(!s){line('新仕様のデータ未生成','#ff9f0a');}
 else {
  line('予算 '+n(s.budget_yen)+'円／登録分残枠 '+n(s.available_yen)+'円','#a9b4c2',10);
  line('実保有登録 '+s.position_count+'件・未登録分は残枠に未反映','#ff9f0a',9);
  const rows=mode==='holdings'?s.holdings:mode==='watch'?s.observations:s.candidates;
  line((mode==='holdings'?'保有':mode==='watch'?'監視':'買い検討候補')+' '+rows.length+'件／コード順','#a9b4c2',10);
  for(const r of rows.slice(0,5)){
   w.addSpacer(6);line(r.code+' '+(r.name||'')+' '+n(r.close)+'円');line(r.status,'#ffd60a',10);
   if(mode==='holdings'){
    line('損益 '+n(r.pnl_yen)+'円／損切 '+n(r.stop_price)+'円','#a9b4c2',10);
    line('管理箱 '+n(r.management_lower)+'〜'+n(r.management_upper),'#a9b4c2',10);
   }else{
    const b=r.box?.active_box;
    if(b)line('箱 '+n(b.lower)+'〜'+n(b.upper)+'／認定 '+b.confirmed_date,'#a9b4c2',9);
    line('前日比 '+n(r.daily_change_pct,2)+'%／出来高 '+n(r.volume_ratio,2)+'倍','#a9b4c2',9);
    line('業種重複 '+(r.sector_check||'未確認'),'#ff9f0a',9);
    if(r.budget_preview)line('予算上限試算 '+n(r.budget_preview.max_shares)+'株・推奨株数ではない','#a9b4c2',9);
   }
  }
  if(!rows.length)line(mode==='holdings'?'実保有は設定ファイルへ登録してください':'該当0件。無理に候補を補充しません。','#a9b4c2',10);
  if(rows.length>5)line('ほか '+(rows.length-5)+'件','#a9b4c2',9);
 }
 line('日付を確認／注文機能なし・日中の損切りは証券口座で','#ff9f0a',9);
} catch(e){line('取得失敗・判定保留','#ff453a');}
Script.setWidget(w);if(!config.runsInWidget)await w.presentLarge();Script.complete();
