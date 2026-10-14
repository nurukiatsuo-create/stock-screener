// 新高値監視 v3：2列。アプリは全件、ウィジェットは抜粋。
const mode=(args.widgetParameter||'watch').trim();
const widget=config.runsInWidget;
const family=config.widgetFamily||'large';
const small=widget&&family==='small';
const short=widget&&(small||family==='medium');
const blocks=[];
const fmt=(x,d=0)=>Number.isFinite(x)?x.toLocaleString('ja-JP',{maximumFractionDigits:d}):'—';
const title=r=>r.code+' '+(r.name||'');
const add=(text,color='#ffffff',size=13)=>blocks.push({text,color,size});
const pending=r=>r.status==='データ確認待ち'||r.box?.valid===false;
function card(r,held=false){
 const lines=[title(r),fmt(r.close)+'円',r.status||'条件該当'];
 if(held){lines.push('損益 '+fmt(r.pnl_yen)+'円','損切 '+fmt(r.stop_price)+'円','管理箱 '+fmt(r.management_lower)+'〜'+fmt(r.management_upper));}
 else{
 const b=r.box?.active_box;
 if(b)lines.push('箱 '+fmt(b.lower)+'〜'+fmt(b.upper));
 lines.push('前日比 '+fmt(r.daily_change_pct,2)+'%','出来高 '+fmt(r.volume_ratio,2)+'倍','業種重複 '+(r.sector_check||'未確認'));
 if(r.budget_preview)lines.push('予算上限 '+fmt(r.budget_preview.max_shares)+'株','（推奨株数ではない）');
 }
 return lines;
}
try{
 const req=new Request('https://raw.githubusercontent.com/nurukiatsuo-create/stock-screener/main/stocks_data.json?t='+Date.now());req.timeoutInterval=20;
 const data=await req.loadJSON(),s=data.strategy;
 add('新高値監視・2列 v3','#ffd60a',17);
 add('日足 '+(data.data_date||'不明')+'／更新 '+(data.updated_at||'不明'),'#a9b4c2',10);
 if(!s||!Array.isArray(s.observations)||!Array.isArray(s.candidates))add('データ未生成・判定保留','#ff9f0a');
 else{
 const held=mode==='holdings';
 const rows=held?(s.holdings||[]):s.candidates;
 add((held?'登録保有 ':'条件該当 ')+rows.length+'件','#ffd60a');
 if(short){
 if(rows.length)add(title(rows[0])+'／詳細はアプリで','#ffd60a',12);
 }else{
 const shown=widget?rows.slice(0,2):rows;
 if(shown.length)blocks.push({cards:shown.map(r=>card(r,held))});
 if(rows.length>shown.length)add('ほか '+(rows.length-shown.length)+'件・アプリで全件','#a9b4c2',10);
 }
 if(!rows.length&&held)add('保有登録なし','#a9b4c2',12);
 if(!held){
 const ids=new Set(rows.map(r=>String(r.code)));
 const watch=s.observations.filter(r=>!ids.has(String(r.code)));
 const limit=widget?(small?1:short?2:rows.length?4:16):watch.length;
 add('監視中 '+watch.filter(r=>!pending(r)).length+'件／保留 '+watch.filter(pending).length+'件','#a9b4c2',12);
 blocks.push({watch:watch.slice(0,limit)});
 if(watch.length>limit)add('ほか '+(watch.length-limit)+'件・アプリで全件','#a9b4c2',10);
 }
 }
}catch(e){add('取得失敗・判定保留','#ff453a');}
if(widget){
 const w=new ListWidget();w.backgroundColor=new Color('#161d26');w.setPadding(14,12,14,12);
 // Fixed safe content width: screen width is not the widget width.
 const contentWidth=small?120:280;
 const wrapper=w.addStack();wrapper.layoutHorizontally();wrapper.addSpacer();
 const body=wrapper.addStack();body.layoutVertically();body.size=new Size(contentWidth,0);
 wrapper.addSpacer();
 const put=(parent,text,size=13,color='#ffffff')=>{const t=parent.addText(text);t.font=Font.systemFont(size);t.textColor=new Color(color);t.lineLimit=1;t.minimumScaleFactor=0.85;return t;};
 for(const b of blocks){
 if(b.text){put(body,b.text,b.size,b.color);body.addSpacer(4);continue;}
 const items=b.cards||b.watch;const cols=small?1:2;
 body.addSpacer(4);
 for(let i=0;i<items.length;i+=cols){
 const row=body.addStack();row.layoutHorizontally();row.topAlignContent();
 for(let j=0;j<cols;j++){
 if(j)row.addSpacer(12);
 const col=row.addStack();col.layoutVertically();
 col.size=new Size((contentWidth-(cols-1)*12)/cols,0);
 const item=items[i+j];if(!item)continue;
 if(b.cards)item.forEach((s,k)=>put(col,s,k===0?14:11,k===2?'#ffd60a':'#ffffff'));
 else put(col,title(item)+(pending(item)?' ※保留':''),14,pending(item)?'#ff9f0a':'#ffffff');
 }
 body.addSpacer(b.cards?6:7);
 }
 }
 // Flexible space only below the content keeps the header at the top.
 w.addSpacer();
 Script.setWidget(w);
}else{
 const table=new UITable();table.showSeparators=true;
 for(const b of blocks){
 if(b.text){const row=new UITableRow();row.height=32;const c=row.addText(b.text);c.titleFont=Font.systemFont(b.size);c.titleColor=new Color(b.color);table.addRow(row);continue;}
 const items=b.cards||b.watch;
 for(let i=0;i<items.length;i+=2){
 const row=new UITableRow();row.cellSpacing=14;
 row.height=b.cards?Math.max(...items.slice(i,i+2).map(x=>x.length))*23+16:48;
 for(let j=0;j<2;j++){
 const item=items[i+j];
 const c=row.addText(!item?'':b.cards?item.join('\n'):title(item)+(pending(item)?'\n判定保留':''));
 c.widthWeight=50;c.titleFont=Font.systemFont(b.cards?14:16);
 if(!b.cards&&item&&pending(item))c.titleColor=new Color('#d98200');
 }
 table.addRow(row);
 }
 }
 await table.present();
}
Script.complete();
