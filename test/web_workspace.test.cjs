/* Behavior regressions for the vanilla-JS workspace. No browser or dependencies required. */
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/main.js'), 'utf8');

function element(id = '') {
    const classes = new Set();
    return {
        id, innerHTML: '', textContent: '', hidden: false, dataset: {}, attributes: {},
        classList: {
            contains: name => classes.has(name),
            add: name => classes.add(name), remove: name => classes.delete(name),
            toggle(name, active) { if (active) classes.add(name); else classes.delete(name); }
        },
        setAttribute(name, value) { this.attributes[name] = value; },
        removeAttribute(name) { delete this.attributes[name]; },
        querySelectorAll() { return []; },
        addEventListener() {}, focus() {}
    };
}

function workspace() {
    const ids = new Map();
    const get = id => { if (!ids.has(id)) ids.set(id, element(id)); return ids.get(id); };
    const sections = ['overview', 'papers', 'policies', 'news', 'industry-reports', 'reports', 'analysis', 'statistics'];
    const nav = sections.map(name => Object.assign(element(), {dataset: {section: name}}));
    const content = sections.map(name => get(name + '-section'));
    const events = {};
    const window = {
        APP_LANGUAGE: 'zh', location: {hash: '#papers'}, errors: [],
        addEventListener(name, callback) { events[name] = callback; }, scrollTo() {}
    };
    const context = vm.createContext({
        window, localStorage: {getItem() { return null; }},
        document: {
            addEventListener() {}, getElementById: get,
            querySelectorAll(selector) { return selector === '.nav-item' ? nav : selector === '.content-section' ? content : []; }
        },
        history: {pushState(data, title, hash) { window.location.hash = hash; }},
        console: {log() {}, warn() {}, error() {}}, URLSearchParams, setTimeout, clearTimeout,
        requestAnimationFrame(callback) { callback(); }
    });
    vm.runInContext(source, context);
    return {context, window, get, events, nav, content, run: code => vm.runInContext(code, context)};
}

test('hash navigation restores the view without clearing filters or duplicating history', () => {
    const app = workspace();
    app.run("state.searchQuery = '储能'; initNavigation()");
    assert.equal(app.run('state.currentSection'), 'papers');
    app.run("navigateToSection('policies')");
    assert.equal(app.window.location.hash, '#policies');
    assert.equal(app.content.filter(item => item.classList.contains('active')).length, 1);
    assert.equal(app.nav[2].attributes['aria-current'], 'page');
    app.window.location.hash = '#papers';
    app.events.popstate();
    assert.equal(app.run('state.currentSection'), 'papers');
    assert.equal(app.run('state.searchQuery'), '储能');
    app.run("navigateToSection('missing')");
    assert.equal(app.run('state.currentSection'), 'papers');
});

test('directory paging uses the requested page and ignores a stale response', async () => {
    const app = workspace();
    const requests = [];
    app.context.fetch = url => new Promise(resolve => requests.push({url, resolve}));
    app.run('renderDirectoryDocuments = (source, docs) => { window.documents = docs; }; renderDirectoryPagination = () => {};');
    const first = app.run("loadDirectory('policy', 1)");
    const second = app.run("loadDirectory('policy', 2)");
    assert.match(requests[1].url, /page=2&per_page=20/);
    requests[1].resolve({ok: true, json: async () => ({documents: [{id: 'new'}], total: 27, total_pages: 2})});
    await second;
    requests[0].resolve({ok: true, json: async () => ({documents: [{id: 'old'}], total: 80, total_pages: 4})});
    await first;
    assert.equal(app.window.documents[0].id, 'new');
    assert.equal(app.run('state.directories.policy.page'), 2);
    assert.equal(app.run('state.directories.policy.total'), 27);
});

test('a stale directory error cannot replace a successful current result', async () => {
    const app = workspace();
    const requests = [];
    app.context.fetch = () => new Promise((resolve, reject) => requests.push({resolve, reject}));
    app.run('renderDirectoryDocuments = () => {}; renderDirectoryPagination = () => {}; showError = (id, message) => window.errors.push(message);');
    const first = app.run("loadDirectory('news')");
    const second = app.run("loadDirectory('news')");
    requests[1].resolve({ok: true, json: async () => ({documents: [], total: 0, total_pages: 0})});
    await second;
    requests[0].reject(new Error('old request failed'));
    await first;
    assert.equal(app.window.errors.length, 0);
});

test('paper API 404 is an empty dataset, while a server failure remains retryable', async () => {
    const app = workspace();
    app.run('renderPapers = () => {}; renderFeaturedPapers = () => {}; renderResearchTrendModules = () => {}; renderResearchMatrix = () => {}; renderComparisonTable = () => {}; showError = (id, message) => window.errors.push(id);');
    app.context.fetch = async () => ({ok: false, status: 404});
    await app.run('loadPapers()');
    assert.equal(app.run('state.papersLoaded'), true);
    assert.equal(app.run('state.paperTotal'), 0);
    assert.equal(app.window.errors.length, 0);
    app.context.fetch = async () => ({ok: false, status: 500});
    await app.run('loadPapers()');
    assert.equal(app.run('state.papersLoaded'), false);
    assert.ok(app.window.errors.includes('papers-list'));
});

test('home leads with source summary, keeps full rationale available, and reports missing dates', () => {
    const app = workspace();
    app.run(`renderTodayRecommendations([{title: '储能发布信息', source_type: 'industry_report',
        summary: '当前只有发布信息，未提供报告全文。', reading_suggestion: {why_relevant: '研究相关性依据'}}])`);
    const html = app.get('today-recommendations').innerHTML;
    assert.ok(html.indexOf('当前只有发布信息') < html.indexOf('研究相关性依据'));
    assert.match(html, /发布日期未提供/);
    assert.doesNotMatch(html, />0\.0</);
    assert.match(html, /<details[\s\S]*研究相关性依据/);
});

test('document links reject unsafe protocols, escape attributes, and do not invent PDF destinations', () => {
    const app = workspace();
    assert.equal(app.run(`sourceLink('javascript:alert(1)', 'source')`), '');
    const malicious = app.run(`sourceLink('https://example.org/" onmouseover="bad', '<title>')`);
    assert.match(malicious, /&quot;/);
    assert.match(malicious, /&lt;title&gt;/);
    assert.doesNotMatch(malicious, /" onmouseover="/);
    const html = app.run(`renderDocumentRow({title:'政策',url:'https://example.org/policy',pdf_url:'https://example.org/policy'},'policy')`);
    assert.doesNotMatch(html, />PDF/);
    assert.doesNotMatch(app.run(`renderRelatedDocuments({related_documents:[{title:'缺失链接'}]})`), /href=/);
});

test('missing scores are omitted while actual zero and applicable dimensions remain meaningful', () => {
    const app = workspace();
    const missing = app.run(`renderRankingPanel({importance_score:null},true)`);
    assert.doesNotMatch(missing, /0\.0|低优先级/);
    assert.match(app.run(`renderRankingPanel({importance_score:0},true)`), /0\.0/);
    const html = app.run(`renderRankingPanel({ranking_applicable_dimensions:['source_credibility'],ranking_score_breakdown:{source_credibility:90,policy_importance:0}})`);
    assert.match(html, /来源可信度/);
    assert.doesNotMatch(html, /政策重要性/);
    assert.match(html, /0–100/);
});

test('papers expose original English abstract alongside system summary and citation metadata', () => {
    const app = workspace();
    const html = app.run(`renderDocumentRow({id:'p',title:'Solar photovoltaics',published:'2021-03-29',abstract:'Full original abstract',summary:'系统摘要内容',authors:['Author'],journal_name:'Joule',citation_count:720},'paper')`);
    for (const value of ['Full original abstract','系统摘要内容','2021-03-29','Joule','720']) assert.ok(html.includes(value));
    const raw = app.run(`renderDocumentRow({id:'raw',abstract:'Publisher abstract',web_card:{summary:'Publisher abstract',source_metadata:{abstract_status:'available',discovered_via:['openalex_search','crossref']}}},'paper')`);
    assert.match(raw, /<h4>原始摘要<\/h4>/);
    assert.doesNotMatch(raw, /<h4>系统摘要<\/h4>/);
    for (const value of ['摘要已获取','openalex_search / crossref']) assert.ok(raw.includes(value));
    const absent = app.run(`renderDocumentRow({id:'absent',web_card:{source_metadata:{abstract_status:'missing'}}},'paper')`);
    assert.match(absent, /摘要待补齐/);
    assert.doesNotMatch(absent, /<h4>系统摘要<\/h4>/);
});

test('paper result feedback distinguishes category total, loaded page, and local matches', () => {
    const app = workspace();
    app.run(`state.paperTotal=45;state.allPapers=Array.from({length:20},()=>({}));state.searchQuery='储能';renderPapers([])`);
    assert.match(app.get('papers-result-count').textContent, /45.*0.*20/);
    assert.match(app.get('paper-applied-filters').textContent, /储能/);
});

test('coverage with no status is not advertised as sufficient', () => {
    const app = workspace();
    app.run(`renderNarrativeCoverage({view:'paper',coverage:{document_count:1,selected_evidence_count:1},limitations:['样本不足']})`);
    const html = app.get('narrative-coverage').innerHTML;
    assert.doesNotMatch(html, /覆盖达标/);
    assert.match(html, /样本不足/);
});

test('chart data keeps actual zero and omits missing values; a topic has a stable color', () => {
    const app = workspace();
    assert.equal(app.run(`JSON.stringify(numericEntries({paper:0,policy:null,news:undefined,report:3}))`), '[["paper",0],["report",3]]');
    assert.equal(app.run(`chartColor('储能')`), app.run(`chartColor('储能')`));
    assert.equal(app.run(`dateRange([{date:'2026-09-22'},{date:'2021-03-29'}])`), '2021-03-29 — 2026-09-22');
});

test('a stale report cannot overwrite the newly selected report type', async () => {
    const app = workspace();
    const requests = [];
    app.context.fetch = url => new Promise(resolve => requests.push({url, resolve}));
    app.run(`renderIntelligenceReport = report => {window.reportTitle=report.title;}`);
    const first = app.run(`loadReport('weekly')`);
    const second = app.run(`loadReport('stage')`);
    requests[1].resolve({ok:true,json:async()=>({title:'阶段报告'})}); await second;
    requests[0].resolve({ok:true,json:async()=>({title:'旧周报'})}); await first;
    assert.match(requests[1].url, /report_type=stage/);
    assert.equal(app.window.reportTitle,'阶段报告');
});

test('forecast evidence uses audited report links and discloses unavailable historical records', () => {
    const app = workspace();
    app.run(`state.report={evidence_indexes:{multi_source:{P01:{document_id:'p',title:'历史论文',url:'',link_status:'http_404'}}}}`);
    assert.equal(app.run(`documentEvidenceIndex(['p']).p.url`), '');
    assert.match(app.run(`documentEvidenceIndex(['missing']).missing.excerpt`), /未加载/);
});

test('home source counts and result feedback use only the newest filtered response', async () => {
    const app = workspace();
    const requests = [];
    app.context.fetch = url => new Promise(resolve => requests.push({url,resolve}));
    app.run(`renderTodayRecommendations=()=>{}; renderSourceSnapshot=counts=>{window.counts=counts;}`);
    const old = app.run('loadIntelligenceHome()');
    app.run(`state.homeFilters={sourceType:'news',topic:'电力',priority:'high',dateFrom:'2026-09-01',dateTo:'2026-09-22'}`);
    const recent = app.run('loadIntelligenceHome()');
    const query = new URLSearchParams(requests[1].url.split('?')[1]);
    for (const [key,value] of Object.entries({source_type:'news',topic:'电力',priority:'high',date_from:'2026-09-01',date_to:'2026-09-22',per_page:'8',sort:'relevance'})) assert.equal(query.get(key),value);
    requests[1].resolve({ok:true,json:async()=>({documents:[{id:'news'}],total:1,source_counts:{news:1}})}); await recent;
    requests[0].resolve({ok:true,json:async()=>({documents:[],total:33,source_counts:{policy:27}})}); await old;
    assert.equal(app.window.counts.news,1);
    assert.match(app.get('intelligence-result-count').textContent,/匹配 1 条 · 展示 1 条/);
});

test('switching narrative views rejects a delayed response from the previous view', async () => {
    const app = workspace();
    const requests=[];
    app.context.fetch = url => new Promise(resolve=>requests.push({url,resolve}));
    app.run(`renderNarrative=()=>{window.view=state.narrative.view;}`);
    const old=app.run('loadNarrative()');
    app.run(`state.narrativeView='multi_source'`);
    const recent=app.run('loadNarrative()');
    requests[1].resolve({ok:true,json:async()=>({view:'multi_source'})}); await recent;
    requests[0].resolve({ok:true,json:async()=>({view:'paper'})}); await old;
    assert.equal(app.window.view,'multi_source');
});

test('category visualization counts labels instead of presenting overlapping labels as percentages', () => {
    const app=workspace();
    app.get('category-chart').parentElement={hidden:false};
    app.context.Chart=function(canvas,config){app.window.chart=config;this.destroy=()=>{};};
    app.run(`state.analysis={document_count:2,statistics:{time_distribution:{'2026-09-22':2},category_distribution:{储能:2,能源系统:2,missing:null}}};renderCategoryChart()`);
    assert.equal(app.window.chart.type,'bar');
    assert.equal(JSON.stringify(app.window.chart.data.datasets[0].data),'[2,2]');
    assert.match(app.get('category-chart-scope').textContent,/一文多标签/);
});


test('paper collection status shows CAS edition and unavailable sources', () => {
    const app = workspace();
    app.run("renderCollectionQuality({raw_count: 900, unique_count: 800, admitted_count: 10, abstract_completeness: .9, cas_editions: [2025], incomplete_count: 20, unavailable_sources: ['semantic_scholar']})");
    const text = app.get('paper-collection-quality').textContent;
    assert.match(text, /2025/);
    assert.match(text, /90.0%/);
    assert.match(text, /semantic_scholar/);
    assert.match(text, /未完成分片 20/);
});
