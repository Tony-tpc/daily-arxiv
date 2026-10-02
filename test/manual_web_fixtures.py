"""Isolated browser QA server; never persists fixture records or changes configuration.

Run with ``python -m test.manual_web_fixtures`` and visit port 5003:
``/?case=fail-once``, ``/?case=sparse``, ``/?case=many``, ``/?case=empty``.
The default page/API responses use the production read-only Flask views.
"""

from flask import Flask, Response, render_template, request

from src.web import app as web_app


def create_fixture_app():
    web_app.app.config['TEMPLATES_AUTO_RELOAD'] = True
    app = Flask(__name__, static_folder=str(web_app.project_root / "static"))

    @app.get("/")
    def index():
        language = 'en' if request.args.get('language') == 'en' else web_app.language
        with web_app.app.app_context():
            html = render_template('index.html', title=web_app.app.config['TITLE'],
                                   description=web_app.app.config['DESCRIPTION'],
                                   language=language, html_lang=language)
        # Intercept only this tab's fetch calls. A reload resets the one-shot errors.
        script = r"""<script>
const scenario = new URLSearchParams(location.search).get('case');
const originalFetch = window.fetch.bind(window);
const seen = new Set();
window.fetch = async (input, options) => {
    const url = new URL(input, location.href);
    const key = url.pathname + (url.searchParams.get('source_type') || '');
    if (['fail','fail-once'].includes(scenario) && url.pathname.startsWith('/api/') && (scenario === 'fail' || !seen.has(key))) {
        seen.add(key);
        return new Response(JSON.stringify({error:'Isolated QA failure'}), {status:503});
    }
    const json = value => Promise.resolve(new Response(JSON.stringify(value), {headers:{'Content-Type':'application/json'}}));
    if (scenario === 'empty' && url.pathname.startsWith('/api/hotspots')) return json({entries:[],empty_reason:'尚未发现满足独立来源数量要求的近期资料。'});
    if (scenario === 'hotspots' && url.pathname.startsWith('/api/hotspots')) {
        const board = url.searchParams.get('board') || (url.pathname.includes('academic') ? 'academic' : 'industry');
        const names = board === 'industry' ? ['新型储能参与电力市场试点发布配套实施细则', '多地推进虚拟电厂接入与需求响应协同', '跨省电力现货交易完善绿电结算机制', '配电网数字化改造进入集中验证阶段', '源网荷储协同示范形成调度评估框架'] : ['面向分布式储能的安全多智能体协同调度', '部分可观测环境下的配电网电压控制', '考虑预测不确定性的源网荷储优化', '需求响应中的隐私保护与分布式决策', '物理约束驱动的电力系统自主控制'];
        const entries = names.map((title,i) => ({id:board+'-fixture-'+i,kind:board,title,rank:i+1,score:board==='industry'?38.6-i*4:5.8-i*.7,source_count:4,paper_count:6,institution_count:3,report_count:5,trend:i===0?'up':'unknown',trend_pct:i===0?12.5:null,summary:'隔离验收样例：梳理实施规则、参与主体与技术约束，关注政策落地后对电力系统调度和储能运行的影响。此数据仅用于界面验收。'}));
        if (url.pathname === '/api/hotspots') return json({entries,computed_at:'2026-10-02T04:00:00+00:00',metric:board==='industry'?'7天 · 独立机构加权报道':'180天 · 去重论文活跃度',coverage:{complete:true}});
        return json({...entries[0],computed_at:'2026-10-02T04:00:00+00:00',summary_kind:'analysis',analysis:{summary:'隔离样例：共同议题综合分析',evidence_ids:['sample-1','sample-2'],sections:(board==='industry'?['events','changes','drivers','impacts','uncertainty','watchpoints']:['question','attention','methods','progress','limitations','next_steps']).map(key=>({key,title:'隔离验收：'+key,text:'跨资料比较共同变化、不同方法与证据局限；此内容仅作排版验收，不进入正式榜单。'.repeat(4),kind:'inference',evidence_ids:['sample-1','sample-2']}))},series:[8,9,13,null,18,23,28].map((score,i)=>({at:`2026-10-01T${String(i+10).padStart(2,'0')}:00:00Z`,score})),evidence:[1,2,3].map((n)=>({id:'sample-'+n,title:'隔离验收：配套规则与试点进展 '+n,source_name:n===1?'主管部门':'专业研究机构',published_at:'2026-10-01T10:00:00+08:00',summary:'围绕市场参与条件、运行约束和效果评估提供证据。',link_status:'unverified'}))});
    }
    if (scenario === 'hotspots' && url.pathname === '/api/research-information') {
        const page = Number(url.searchParams.get('page') || 1);
        return json({total:12,source_counts:{paper:6,policy:2,news:3,industry_report:1},documents:Array.from({length:page===1?8:4},(_,i)=>({id:'qa-'+page+'-'+i,title:'隔离验收：物理约束下的能源系统协同决策 '+(i+1),display_title:['分布式储能协同调度：从算法验证到实际约束','虚拟电厂参与现货市场的关键机制与试点经验','面向能源智能体的安全控制与可解释决策'][i%3],summary:'这份资料关注能源系统中的实际决策问题，讨论约束条件、证据来源与可复用的方法。仅用于视觉验收，不进入正式资料库。',published_at:i<3?'2026-10-02':'2026-10-01',source_type:['paper','policy','news'][i%3],source_name:'隔离测试来源',editorial:{status:'complete',score:86-i},hotspot_id:'industry-fixture-0'}))});
    }
    if (['sparse','many','empty'].includes(scenario) && ['/api/papers','/api/documents'].includes(url.pathname)) {
        const isPaper = url.pathname === '/api/papers';
        const page = Number(url.searchParams.get('page') || 1), size = Number(url.searchParams.get('per_page') || 20);
        const total = scenario === 'empty' ? 0 : scenario === 'many' ? 45 : 1;
        const records = Array.from({length:total}, (_,i) => ({id:'fixture-'+i,
            title: (isPaper ? 'Evaluating autonomous decision-making under physical energy constraints: ' : '隔离测试：关于推进能源物理系统感知决策控制及源网荷储协同研究的实施说明') + (i+1),
            abstract: isPaper ? 'Original English abstract. '.repeat(80) : undefined,
            summary: '隔离测试资料，仅用于检查长文本和缺失字段，不进入真实资料库。'.repeat(12),
            importance_score: null, source_type: isPaper ? 'paper' : url.searchParams.get('source_type')
        }));
        return json({[isPaper?'papers':'documents']:records.slice((page-1)*size,page*size),total,page,per_page:size,total_pages:Math.ceil(total/size)});
    }
    if (scenario === 'empty' && url.pathname === '/api/research-information') return json({documents:[],total:0,source_counts:{}});
    return originalFetch(input, options);
};
</script>"""
        return html.replace('<script src="/static/js/main.js">', script + '<script src="/static/js/main.js">')

    @app.get("/api/<path:endpoint>")
    def api(endpoint):
        with web_app.app.test_client() as client:
            result = client.get(request.full_path)
            return Response(result.get_data(), status=result.status_code, content_type=result.content_type)

    @app.get("/images/<path:filename>")
    def images(filename):
        with web_app.app.test_client() as client:
            result = client.get(request.full_path)
            return Response(result.get_data(), status=result.status_code, content_type=result.content_type)

    return app


if __name__ == "__main__":
    create_fixture_app().run(host="127.0.0.1", port=5003, debug=False)
