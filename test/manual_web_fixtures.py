"""Isolated browser QA server; never persists fixture records or changes configuration.

Run with ``python -m test.manual_web_fixtures`` and visit port 5002:
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
    if (scenario === 'fail-once' && url.pathname.startsWith('/api/') && !seen.has(key)) {
        seen.add(key);
        return new Response(JSON.stringify({error:'Isolated QA failure'}), {status:503});
    }
    const json = value => Promise.resolve(new Response(JSON.stringify(value), {headers:{'Content-Type':'application/json'}}));
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
    create_fixture_app().run(host="127.0.0.1", port=5002, debug=False)
