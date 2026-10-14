// Scriptable: default/watch/candidates = candidates + compact watch list; holdings = positions.
// App run opens the full list. Widgets show a subset. No orders.
const mode=(args.widgetParameter||'watch').trim();
const w=new ListWidget();w.backgroundColor=new Color('#161d26');w.setPadding(12,12,12,12);
const lines=[];
function line(s,color='#ffffff',size=11){lines.push({s,color,size});}
function n(x,d=0){return Number.isFinite(x)?x.toLocaleString('ja-JP',{maximumFractionDigits:d}):'—';}
function name(r){return r.code+' '+(r.name||'');}
function detail(r,held=false){
 line(name(r)+' '+n(r.close)+'円','#ffffff',12);
 line(r.status||'条件該当','#ffd60a',10);
 if(held){line('損益 '+n(r.pnl_yen)+'円／損切 '+n(r.stop_price)+'円');line('管理箱 '+n(r.management_lower)+'〜'+n(r.management_upper));return;}
 const b=r.box?.active_box;if(b)line('箱 '+n(b.lower)+'〜'+n(b.upper),'#a9b4c2',10);
 line('前日比 '+n(r.daily_change_pct,2)+'%／出来高 '+n(r.volume_ratio,2)+'倍','#a9b4c2',10);
 line('業種重複 '+(r.sector_check||'未確認'),'#ff9f0a',9);
 if(r.budget_preview)line('予算上限 '+n(r.budget_preview.max_shares)+'株（推奨ではない）','#a9b4c2',9);
}
try{
 const req=new Request('https://raw.githubusercontent.com/nurukiatsuo-create/stock-screener/main/stocks_data.json?t='+Date.now());req.timeoutInterval=20;
 const data=await req.loadJSON(),s=data.strategy;
 line('新高値・ボックス監視','#ffd60a',16);
 line('日足 '+(data.data_date||'不明')+'／更新 '+(data.updated_at||'不明'),'#a9b4c2',9);
 if(!s||!Array.isArray(s.observations)||!Array.isArray(s.candidates)){line('監視データ未生成・判定保留','#ff9f0a');}
 else if(mode==='holdings'){
 const rows=s.holdings||[];line('実保有登録 '+rows.length+'件','#a9b4c2');
 const shown=config.runsInWidget?rows.slice(0,2):rows;shown.forEach(r=>detail(r,true));
 if(!rows.length)line('実保有は設定ファイルへ登録してください');
 if(rows.length>shown.length)line('ほか '+(rows.length-shown.length)+'件／アプリで全件');
 }else{
 const candidates=s.candidates,ids=new Set(candidates.map(r=>r.code));
 const watch=s.observations.filter(r=>!ids.has(r.code));
 line('条件該当 '+candidates.length+'件／その他 '+watch.length+'件','#a9b4c2',10);
 const shown=config.runsInWidget?candidates.slice(0,config.widgetFamily==='small'?1:2):candidates;
 shown.forEach(r=>detail(r));
 if(!candidates.length)line('条件該当なし・見送り','#ffd60a',10);
 if(candidates.length>shown.length)line('条件該当ほか '+(candidates.length-shown.length)+'件','#ffd60a',9);
 const limit=config.widgetFamily==='small'?2:candidates.length?3:8;
 const compact=config.runsInWidget?watch.slice(0,limit):watch;
 for(const r of compact){const pending=r.status==='データ確認待ち'||r.box?.valid===false;line(name(r)+'｜'+(pending?'判定保留':'監視中'),pending?'#ff9f0a':'#a9b4c2',10);}
 if(watch.length>compact.length)line('ほか '+(watch.length-compact.length)+'件／アプリで全件','#a9b4c2',9);
 }
 line('日付を確認・注文機能なし','#ff9f0a',9);
}catch(e){line('取得失敗・判定保留','#ff453a');}
if(config.runsInWidget){for(const x of lines){const t=w.addText(x.s);t.textColor=new Color(x.color);t.font=Font.systemFont(x.size);}Script.setWidget(w);}
else{const table=new UITable();for(const x of lines){const row=new UITableRow();row.height=34;const cell=row.addText(x.s);cell.titleFont=Font.systemFont(x.size+2);table.addRow(row);}await table.present();}
Script.complete();
