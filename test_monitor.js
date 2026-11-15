// Pure ranking checks; Scriptable UI globals are not required.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('NewHighMonitor.js','utf8');
const context={};vm.createContext(context);
vm.runInContext(src.slice(src.indexOf('const pending='),src.indexOf('function gapLabel')),context);
const rank=context.rankWaiting,date='2026-10-16';
const r={entry_group:'post_break',code:'7094',close:1912,box:{valid:true,date,active_box:{lower:1764.42,upper:1893.65,confirmed_date:'2026-10-05',breakout_date:date}}};
const board={watching:[{code:'7094',evidence:{data_valid:true,today:{date,reference_high:2244.412}}}]};
const rows=rank([r],board,date);
assert.equal(rows.length,1);assert.equal(rows[0].afterBreak,true);
assert.equal(rows[0].boxGap,0);assert.ok(Math.abs(rows[0].highGap-17.3856)<0.001);
assert.equal(rank([{...r,close:1850}],board,date).length,0);
assert.equal(rank([{...r,box:{...r.box,date:'2026-10-15'}}],board,date).length,0);
assert.equal(rank([r],{},date).length,0);
assert.equal(rank([{...r,box:{...r.box,active_box:{...r.box.active_box,breakdown_date:date}}}],board,date).length,0);
const before={...r,entry_group:'pre_break',close:1849,box:{...r.box,active_box:{...r.box.active_box,breakout_date:null}}};
assert.equal(rank([before],board,date)[0].afterBreak,false);
console.log('Monitor: box interior, post-break, return, breakdown and stale/missing data passed');

assert.equal(rank([{...r,entry_group:'other'}],board,date).length,0);


// Audit state must override pre/post-break classification in old cached rows.
assert.equal(rank([{...before,selection_status:'pending'}],board,date).length,0);
assert.equal(rank([{...r,selection_status:'excluded'}],board,date).length,0);
assert.equal(vm.runInContext("pending({selection_status:'excluded',box:{valid:false}})",context),false);

async function render(data,widget=false){
 const texts=[];
 const parent=()=>({addText:s=>{texts.push(s);return {};},addStack:()=>parent(),addSpacer(){},
  layoutHorizontally(){},layoutVertically(){},topAlignContent(){},setPadding(){}});
 const ui={args:{},config:{runsInWidget:widget,widgetFamily:'large'},
  Request:class{async loadJSON(){return data;}},
  UITable:class{addRow(){} async present(){}},
  UITableRow:class{addText(s){texts.push(s);return {};}},
  Color:class{},Size:class{},Font:{systemFont:()=>({})},
  ListWidget:class{constructor(){return parent();}},Script:{setWidget(){},complete(){}}};
 vm.createContext(ui);await vm.runInContext('(async()=>{'+src+'})()',ui);return texts.join('\n');
}
(async()=>{
 const data={data_date:date,updated_at:'10/16 16:00',breakout_board:board,strategy:{version:3,
  selection_version:1,selection_as_of:date,candidates:[],
  observations:[{...before,name:'確認対象',selection_status:'pending',status:'確認待ち：四季報',
   selection_reasons:['四季報原本未照合','TOPIX公式リスト未確認'],technical_status:'突破直前・未突破'}],
  selection_counts:{by_gate:{fundamental:{unknown:1},topix:{unknown:1}},not_calculated_codes:['5678']}}};
 const app=await render(data);
 assert.ok(app.includes('確認済み候補 0件'));
 assert.ok(app.includes('TOPIX公式リスト未確認'));
 assert.ok(app.includes('突破直前・距離順 0件'));
 assert.ok(app.includes('株価未計算 1銘柄'));
 const widget=await render(data,true);
 assert.ok(widget.includes('確認待ち 1'));
 console.log('Monitor: app/widget audit states, reasons and schema compatibility passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
