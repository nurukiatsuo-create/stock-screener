// 新高値監視 v6：初動・突破直前・突破後を分離。
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
// Distance is required rise from the latest confirmed close, not a buy score.
function rankWaiting(observations, board, dataDate) {
 const evidence=new Map();
 for(const group of Object.values(board||{})){
 if(!Array.isArray(group))continue;
 for(const r of group){const e=r.evidence,t=e?.today;
 if(e?.data_valid&&t?.date===dataDate)evidence.set(String(r.code),t);}
 }
 return observations.flatMap(r=>{
 if(!['pre_break','post_break'].includes(r.entry_group))return [];
 const b=r.box?.active_box,t=evidence.get(String(r.code)),c=r.close;
 if(pending(r)||r.box?.valid!==true||r.box.date!==dataDate||!b||!b.confirmed_date||b.breakdown_date)return [];
 if(![c,b.lower,b.upper,t?.reference_high].every(x=>Number.isFinite(x)&&x>0)||b.lower>=b.upper||c<b.lower)return [];
 const afterBreak=Boolean(b.breakout_date);
 if(afterBreak?(b.breakout_date>dataDate||c<=b.upper):c>b.upper)return [];
 const boxGap=Math.max(0,(b.upper/c-1)*100),highGap=Math.max(0,(t.reference_high/c-1)*100);
 return [{...r,boxGap,highGap,afterBreak,remaining:Math.max(boxGap,highGap)}];
 }).sort((a,b)=>a.remaining-b.remaining||String(a.code).localeCompare(String(b.code)));
}
function gapLabel(x){return x<=0?'到達':x<0.1?'0.1%未満':fmt(x,1)+'%';}
function watchText(r){if(r.entry_group==='post_break')return title(r)+'\n'+r.status+'\n箱から '+fmt(r.close_vs_box_upper_pct,1)+'%';return Number.isFinite(r.remaining)?title(r)+'\n突破まで '+gapLabel(r.remaining)+'\n'+(r.afterBreak?'箱突破済':'箱 '+gapLabel(r.boxGap))+'／高値 '+gapLabel(r.highGap):title(r)+'\n'+(pending(r)?'判定保留':r.status||'その他監視');}
function card(r,held=false){
 const lines=[title(r),fmt(r.close)+'円',r.status||'条件該当'];
 if(held){lines.push('損益 '+fmt(r.pnl_yen)+'円','損切 '+fmt(r.stop_price)+'円','管理箱 '+fmt(r.management_lower)+'〜'+fmt(r.management_upper));}
 else{
 const b=r.box?.active_box;
 if(b)lines.push('箱 '+fmt(b.lower)+'〜'+fmt(b.upper));
 if(r.entry_event)lines.push('初回突破 '+r.entry_event.date+'／出来高 '+fmt(r.entry_event.volume_ratio_prior20,2)+'倍');
 lines.push('前日比 '+fmt(r.daily_change_pct,2)+'%','出来高 '+fmt(r.volume_ratio,2)+'倍','業種重複 '+(r.sector_check||'未確認'));
 lines.push('業績・事業変化は要確認');
 }
 return lines;
}
try{
 const req=new Request('https://raw.githubusercontent.com/nurukiatsuo-create/stock-screener/main/stocks_data.json?t='+Date.now());req.timeoutInterval=20;
 const data=await req.loadJSON(),s=data.strategy;
 add('新高値監視・初動 v6','#ffd60a',17);
 add('日足 '+(data.data_date||'不明')+'／更新 '+(data.updated_at||'不明'),'#a9b4c2',10);
 if(!s||s.version!==3||!Array.isArray(s.observations)||!Array.isArray(s.candidates))add('データ未生成・判定保留','#ff9f0a');
 else{
 const held=mode==='holdings';
 const rows=held?(s.holdings||[]):s.candidates;
 add((held?'登録保有 ':'初動・技術条件 ')+rows.length+'件','#ffd60a');
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
 const waiting=rankWaiting(watch,data.breakout_board,data.data_date);
 const waitingIds=new Set(waiting.map(r=>String(r.code)));
 const others=watch.filter(r=>!waitingIds.has(String(r.code))&&!pending(r));
 const heldBack=watch.filter(pending);
 const pre=waiting.filter(r=>r.entry_group==='pre_break');
 const post=waiting.filter(r=>r.entry_group==='post_break');
 const limit=widget?(short?0:rows.length?1:3):Math.max(pre.length,post.length);
 for(const [label,group] of [['突破直前・距離順',pre],['突破後の追跡・新規候補外',post]]){
 add(label+' '+group.length+'件','#a9b4c2',12);
 if(limit&&group.length)blocks.push({watch:group.slice(0,limit)});
 if(group.length>limit)add('ほか '+(group.length-limit)+'件・アプリで全件','#a9b4c2',10);
 }
 add('その他監視 '+others.length+'件／保留 '+heldBack.length+'件','#a9b4c2',10);
 if(!widget){
 add('距離＝終値から必要な上昇率。両水準を超える終値を待つ。','#a9b4c2',11);
 add('距離は買い推奨や上昇確率ではありません。','#a9b4c2',11);
 add('その他監視（コード順）','#a9b4c2',13);blocks.push({watch:others});
 add('判定保留','#ff9f0a',13);blocks.push({watch:heldBack});
 }
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
 else {put(col,title(item),14,pending(item)?'#ff9f0a':'#ffffff');
 if(item.entry_group==='post_break'){put(col,item.status,10,'#a9b4c2');put(col,'箱から '+fmt(item.close_vs_box_upper_pct,1)+'%',10,'#7dd3fc');}
 else if(Number.isFinite(item.remaining)){put(col,'突破まで '+gapLabel(item.remaining),12,'#7dd3fc');put(col,(item.afterBreak?'箱突破済':'箱 '+gapLabel(item.boxGap))+'／高値 '+gapLabel(item.highGap),9,item.afterBreak?'#ffd60a':'#a9b4c2');}
 else put(col,pending(item)?'判定保留':item.status||'その他監視',10,'#a9b4c2');}
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
 row.height=b.cards?Math.max(...items.slice(i,i+2).map(x=>x.length))*23+16:items.slice(i,i+2).some(x=>Number.isFinite(x.remaining))?78:48;
 for(let j=0;j<2;j++){
 const item=items[i+j];
 const c=row.addText(!item?'':b.cards?item.join('\n'):watchText(item));
 c.widthWeight=50;c.titleFont=Font.systemFont(b.cards?14:16);
 if(!b.cards&&item&&pending(item))c.titleColor=new Color('#d98200');
 }
 table.addRow(row);
 }
 }
 await table.present();
}
Script.complete();
