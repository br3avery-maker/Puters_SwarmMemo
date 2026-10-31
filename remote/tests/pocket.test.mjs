import assert from 'node:assert/strict';
import {test} from 'node:test';
import {SCHEMA,digestText,validPath,mergeThread,inventory,inspectManifest,verifyInventory} from '../lib/pocket.mjs';

test('hashes Unicode by UTF-8 and standard SHA256', () => {
  assert.equal(digestText(''), 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
  assert.equal(digestText('hi'), '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4');
});
test('rejects traversal and bad paths', () => {
  for (const path of ['../x','a/../b','/x','a\\b','a//b','a/./b','']) assert.throws(()=>validPath(path));
});
test('inventory distinguishes paths and hashes', () => {
  const v=inventory([{path:'b.txt',text:'x'},{path:'a.txt',text:'x'}]);
  assert.equal(v.schema, SCHEMA);
  assert.equal(v.files.length,2);
  assert.equal(v.files[0].path,'a.txt');
  assert.equal(v.files[0].sha256,v.files[1].sha256);
});
test('duplicates fail deterministically',()=>assert.throws(()=>inventory([{path:'x',text:''},{path:'x',text:''}])));
test('verify detects every difference', () => {
  const original=inventory([{path:'a',text:'hi'},{path:'missing',text:'x'}]);
  const changed=verifyInventory(original,[{path:'a',text:'bye'},{path:'extra',text:''}]);
  assert.deepEqual(changed,{ok:false,missing:['missing'],extra:['extra'],modified:['a']});
});
test('manifest rejects conflicting paths or hashes', () => {
  const m=inventory([{path:'one',text:'1'}]);
  assert.equal(inspectManifest(m).files,1);
  assert.throws(()=>inspectManifest({...m,files:[...m.files,...m.files]}));
  assert.throws(()=>inspectManifest({...m,files:[{path:'two',size:1,sha256:'oops'}]}));
});
test('merge thread retains prior state and tracks edits', () => {
  const s={root_id:'r', cursor:'c', seen:[]};
  const a=mergeThread(s,{ok:true,data:{root_id:'r',messages:[{id:'m',text:'hello'}],next_cursor:'d'}});
  assert.deepEqual(a.new_ids,['m']);
  assert.equal(s.cursor,'c');
  assert.equal(a.state.cursor,'d');
  const b=mergeThread(a.state,{ok:true,data:{root_id:'r',messages:[{id:'m',text:'goodbye'}]}});
  assert.deepEqual(b.changed_ids,['m']);
  assert.equal(b.state.cursor,'d');
});
test('failed or wrong root never advances',()=>{
  const state={root_id:'r',cursor:'old',seen:[]};
  assert.throws(()=>mergeThread(state,{ok:false,next_cursor:'bad'}));
  assert.throws(()=>mergeThread(state,{ok:true,data:{root_id:'wrong'}}));
  assert.equal(state.cursor,'old');
});
test('top-level messages format accepted',()=>{
  const r=mergeThread({root_id:'r',seen:[]},{ok:true,data:{root_id:'r'},messages:[{id:'m',text:'yo'}]});
  assert.deepEqual(r.new_ids,['m']);
});
