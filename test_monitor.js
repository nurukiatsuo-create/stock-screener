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
