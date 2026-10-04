const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function workspace() {
    const nodes = new Map();
    const get = id => {
        if (!nodes.has(id)) nodes.set(id, {innerHTML:'', querySelector:()=>null, insertAdjacentHTML(_,text){this.innerHTML += text;}});
        return nodes.get(id);
    };
    const requests = [];
    const state = {homePage:2};
    const context = vm.createContext({LANG:'zh', state, window:{location:{hash:'#hotspot/industry-test'}},
        document:{getElementById:get,addEventListener(){}},
        escapeHtml:value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
        sourceLink:(url,title)=>`<a href="${url}">${title}</a>`, updateElement(){}, emptyState:text=>text,
        fetch:url=>new Promise((resolve,reject)=>requests.push({url,resolve,reject}))});
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/js/hotspots.js'),'utf8'),context);
    return {api:context.window.EnergyHotspots,get,requests,state};
}
const entry = title => ({id:'industry-test',kind:'industry',title,rank:1,score:12,source_count:2,report_count:3});

test('published boards still expose stale source warnings safely', async () => {
    const {api,get,requests}=workspace();
    const pending=api.loadBoard('industry');
    requests[0].resolve({ok:true,json:async()=>({entries:[entry('有效议题')],processing:{
        pending_collection:2,failed_sources:[{name:'过期来源',error:'<script>stale</script>'}]
    }})});
    await pending;
    assert.match(get('hot-industry-meta').innerHTML,/采集覆盖不完整/);
    assert.match(get('hot-industry-meta').innerHTML,/待补采 2/);
    assert.match(get('hot-industry-meta').innerHTML,/&lt;script&gt;stale/);
    assert.doesNotMatch(get('hot-industry-meta').innerHTML,/<script>/);
    assert.match(get('home-hot-industry').innerHTML,/有效议题/);
});

test('board refresh rejects a late response and escapes external titles', async () => {
    const {api,get,requests}=workspace();
    const old=api.loadBoard('industry'), current=api.loadBoard('industry',true);
    requests[1].resolve({ok:true,json:async()=>({entries:[entry('<script>new</script>')]})}); await current;
    requests[0].resolve({ok:true,json:async()=>({entries:[entry('old')]})}); await old;
    assert.match(get('home-hot-industry').innerHTML,/&lt;script&gt;new/);
    assert.doesNotMatch(get('home-hot-industry').innerHTML,/<script>|>old</);
});

test('navigation away invalidates an in-flight detail request', async () => {
    const {api,get,requests}=workspace();
    const pending=api.loadDetail('industry-test');
    api.navigate('overview');
    requests[0].resolve({ok:true,json:async()=>entry('must not render')}); await pending;
    assert.doesNotMatch(get('hotspot-detail').innerHTML,/must not render/);
});

test('missing details differ from a retryable server failure', async () => {
    const {api,get,requests}=workspace();
    let pending=api.loadDetail('missing');
    requests[0].resolve({status:404}); await pending;
    assert.match(get('hotspot-detail').innerHTML,/热点暂无可用证据/);
    pending=api.loadDetail('failed');
    requests[1].resolve({status:503,ok:false}); await pending;
    assert.match(get('hotspot-detail').innerHTML,/data-retry-detail="failed"/);
});

test('empty rankings and unverified evidence do not invent links or charts', () => {
    const {api}=workspace();
    const html=api.renderDetail({...entry('主题'),evidence:[{title:'尚未核验',url:'https://example.com',link_status:'unverified'}]});
    assert.match(html,/尚无足够的可比历史/);
    assert.doesNotMatch(html,/href="https:\/\/example.com"/);
});

test('analysis precedes folded evidence with member citations and small nonzero activity', () => {
    const {api}=workspace();
    const html=api.renderDetail({...entry('研究主题'),kind:'academic',score:.006,
        analysis:{evidence_ids:['a'],sections:[{title:'方法比较',text:'<unsafe>比较',kind:'inference',evidence_ids:['a','outside']}]},
        evidence:[{id:'a',title:'证据 A',doi:'10.1234/a',original_text:'Original abstract',link_status:'unverified'}]});
    assert.match(html,/0\.0060/);
    assert.match(html,/&lt;unsafe&gt;比较/);
    assert.match(html,/data-hot-evidence="a"/);
    assert.doesNotMatch(html,/data-hot-evidence="outside"/);
    assert.ok(html.indexOf('方法比较')<html.indexOf('证据与进展'));
    assert.match(html,/<details><summary>原始摘要 \/ 正文/);
});

test('history uses actual zero and breaks paths at missing collection intervals', () => {
    const {api}=workspace();
    const html=api.sparkline([0,null,1,2].map((score,i)=>({at:`2026-10-02T0${i}:00:00Z`,score})));
    assert.match(html,/M8.00,112.00 M/);
    assert.match(html,/L/);
    assert.doesNotMatch(html,/NaN/);
});

test('selected feed pagination exposes current page and boundaries', () => {
    const {api,get}=workspace();
    api.renderFeedPagination({total:12});
    assert.match(get('home-feed-pagination').innerHTML,/2 \/ 2/);
    assert.match(get('home-feed-pagination').innerHTML,/data-feed-page="3" disabled/);
    api.renderFeedPagination({total:0});
    assert.equal(get('home-feed-pagination').innerHTML,'');
});


test('empty boards show processing progress and never fall back to single documents', async () => {
    const {api,get,requests}=workspace();
    const pending=api.loadBoard('academic');
    requests[0].resolve({ok:true,json:async()=>({entries:[],discovery:[{
        id:'single', title:'<script>paper</script>',summary:'Real abstract',selected:true,
        source_name:'Journal',published_at:'2026-09-01',url:'https://unverified.example',link_status:'unverified'
    }],processing:{eligible_documents:31,ready_documents:19,pending_documents:2,awaiting_content:12}})});
    await pending;
    const home=get('home-hot-academic').innerHTML, full=get('hot-academic-list').innerHTML;
    assert.match(home,/31/);
    assert.match(home,/19/);
    assert.doesNotMatch(full,/Real abstract|paper|学术精选/);
    assert.doesNotMatch(full,/hot-rank|hot-value|href="https:\/\/unverified.example"|<script>/);
});
