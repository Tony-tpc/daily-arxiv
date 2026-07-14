"""
Flask Web 应用

展示 arXiv 论文分析结果
"""
import os
import sys
import json
from copy import deepcopy
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify, request, send_from_directory
# from flask_cors import CORS  # 暂时注释，本地开发不需要
import markdown

from src.ranking.relevance_ranker import RelevanceRanker
from src.utils import load_config, load_json, get_language


# 创建 Flask 应用
# 指定模板和静态文件路径为项目根目录
app = Flask(
    __name__,
    template_folder=str(project_root / 'src' / 'web' / 'templates'),
    static_folder=str(project_root / 'static'),
    static_url_path='/static'
)
# CORS(app)  # 暂时注释，本地开发不需要

# 加载配置
config = load_config()
web_config = config.get('web', {})
language = get_language(config)
relevance_ranker = RelevanceRanker(config)
DIRECTORY_SOURCE_TYPES = {"policy", "news", "industry_report"}

WEB_I18N = {
    'zh': {
        'html_lang': 'zh-CN',
        'title_default': 'Daily arXiv - AI Research Tracker',
        'description_default': '每日追踪最新的 AI 研究论文',
        'error_no_analysis': '没有找到分析数据',
        'error_no_papers': '没有找到论文数据',
        'error_no_summaries': '没有找到总结数据',
        'error_paper_not_found': '论文不存在',
        'web_start': 'Daily arXiv Web 服务启动',
        'access_url': '访问地址',
        'api_doc': 'API 文档',
        'stop_hint': '按 Ctrl+C 停止服务',
    },
    'en': {
        'html_lang': 'en-US',
        'title_default': 'Daily arXiv - AI Research Tracker',
        'description_default': 'Track the latest AI research papers daily',
        'error_no_analysis': 'Analysis data not found',
        'error_no_papers': 'Paper data not found',
        'error_no_summaries': 'Summary data not found',
        'error_paper_not_found': 'Paper not found',
        'web_start': 'Daily arXiv Web Service Started',
        'access_url': 'Access URL',
        'api_doc': 'API docs',
        'stop_hint': 'Press Ctrl+C to stop the service',
    }
}


def t(key: str) -> str:
    return WEB_I18N[language].get(key, key)

app.config['TITLE'] = web_config.get('title', t('title_default'))
app.config['DESCRIPTION'] = web_config.get('description', t('description_default'))


def _load_papers_data() -> dict:
    """Load paper records, preferring OpenAlex search or enriched snapshots when available."""
    for candidate in ['data/papers/latest_openalex.json', 'data/papers/latest_enriched.json']:
        data = load_json(candidate)
        if data and data.get('papers'):
            return data
    return load_json('data/papers/latest.json') or {}


def _load_summaries_by_id() -> dict:
    summaries_data = load_json('data/summaries/latest.json') or {}
    summaries = summaries_data.get('summaries') or summaries_data.get('papers', [])
    summary_index = {}
    for summary in summaries:
        paper_id = summary.get('paper_id') or summary.get('id')
        if paper_id:
            summary_index[paper_id] = summary
    return summary_index


def _load_intelligence_documents() -> list[dict]:
    """Load the latest canonical mixed-source snapshot without duplicating records."""
    documents: list[dict] = []
    for candidate in ('data/documents/latest.json', 'data/summaries/latest.json'):
        payload = load_json(candidate) or {}
        candidate_documents = (
            payload.get('documents')
            or payload.get('summaries')
            or payload.get('papers')
            or []
        )
        if candidate_documents:
            documents = [item for item in candidate_documents if isinstance(item, dict)]
            break

    unique_documents = {}
    for document in documents:
        document_id = str(document.get('id') or document.get('url') or document.get('title') or '')
        if document_id:
            unique_documents[document_id] = document
    return list(unique_documents.values())


def _build_document_from_paper(paper: dict, summary_record: dict | None = None):
    summary_record = summary_record or {}
    document = deepcopy(paper)
    document.update(summary_record)
    document.setdefault('source_type', 'paper')
    document.setdefault('source_name', 'arXiv')
    document.setdefault('summary', paper.get('summary', ''))
    document.setdefault('authors_or_orgs', paper.get('authors', []))
    document.setdefault('published_at', paper.get('published', ''))
    document.setdefault('collected_at', paper.get('fetched_at', ''))
    document.setdefault('url', paper.get('entry_url') or paper.get('pdf_url') or '')
    document.setdefault('raw_text', paper.get('abstract', ''))
    document.setdefault('keywords', paper.get('categories', []))
    document.setdefault(
        'tags',
        paper.get('categories', []) + paper.get('openalex_topics', []),
    )
    document.setdefault(
        'entities',
        paper.get('authors', []) + paper.get('openalex_institutions', []),
    )
    document.setdefault('arxiv_id', paper.get('id'))
    document.setdefault('categories', paper.get('categories', []))
    return document


def _build_paper_response(paper: dict, summary_record: dict | None = None) -> dict:
    summary_record = summary_record or {}
    document = _build_document_from_paper(paper, summary_record)
    return relevance_ranker.rank_document(document)


@app.route('/')
def index():
    """主页"""
    return render_template('index.html',
                         title=app.config['TITLE'],
                         description=app.config['DESCRIPTION'],
                         language=language,
                         html_lang=t('html_lang'))


@app.route('/api/analysis')
def get_analysis():
    """获取趋势分析数据"""
    try:
        # 加载最新的分析数据
        analysis_data = load_json('data/analysis/latest.json')
        
        if not analysis_data:
            return jsonify({'error': t('error_no_analysis')}), 404
        
        # 处理 LLM 分析的 Markdown 内容
        llm_analysis = analysis_data.get('llm_analysis', {})
        for key in ['analysis_summary', 'hotspots', 'trends', 'future_directions', 'research_ideas']:
            if key in llm_analysis and llm_analysis[key]:
                # 将 Markdown 转换为 HTML
                llm_analysis[f'{key}_html'] = markdown.markdown(
                    llm_analysis[key],
                    extensions=['tables', 'fenced_code', 'nl2br']
                )
        
        return jsonify(analysis_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/papers')
def get_papers():
    """获取论文列表"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category', '')
        
        # 加载论文数据
        papers_data = _load_papers_data()
        
        if not papers_data.get('papers'):
            return jsonify({'error': t('error_no_papers')}), 404
        
        papers = papers_data.get('papers', [])
        summary_index = _load_summaries_by_id()
        
        # 按类别过滤
        if category:
            papers = [p for p in papers if category in p.get('categories', [])]

        ranked_papers = [
            _build_paper_response(paper, summary_index.get(paper.get('id')))
            for paper in papers
        ]
        ranked_papers.sort(
            key=lambda item: float(item.get('importance_score') or 0),
            reverse=True,
        )
        
        # 分页
        total = len(ranked_papers)
        start = (page - 1) * per_page
        end = start + per_page
        papers_page = ranked_papers[start:end]
        
        return jsonify({
            'papers': papers_page,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'date': papers_data.get('date')
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/papers/<paper_id>')
def get_paper_detail(paper_id):
    """获取论文详情（包括总结）"""
    try:
        # 加载论文数据
        papers_data = _load_papers_data()
        papers = papers_data.get('papers', [])
        
        # 查找论文
        paper = None
        for p in papers:
            if p.get('id') == paper_id:
                paper = p
                break
        
        if not paper:
            return jsonify({'error': t('error_paper_not_found')}), 404
        
        # 加载总结数据
        summary_index = _load_summaries_by_id()
        enriched_paper = _build_paper_response(paper, summary_index.get(paper_id))

        return jsonify(enriched_paper)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/summaries')
def get_summaries():
    """获取论文总结列表"""
    try:
        summaries_data = load_json('data/summaries/latest.json')
        
        if not summaries_data:
            return jsonify({'error': t('error_no_summaries')}), 404
        
        return jsonify(summaries_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories')
def get_categories():
    """获取所有类别"""
    try:
        papers_data = _load_papers_data()
        
        if not papers_data.get('papers'):
            return jsonify({'error': t('error_no_papers')}), 404
        
        papers = papers_data.get('papers', [])
        
        # 统计类别
        categories = {}
        for paper in papers:
            for cat in paper.get('categories', []):
                categories[cat] = categories.get(cat, 0) + 1
        
        # 转换为列表并排序
        category_list = [
            {'name': cat, 'count': count}
            for cat, count in categories.items()
        ]
        category_list.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify(category_list)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """获取统计信息"""
    try:
        # 加载数据
        papers_data = _load_papers_data()
        summaries_data = load_json('data/summaries/latest.json')
        analysis_data = load_json('data/analysis/latest.json')
        knowledge_data = load_json('data/knowledge/latest.json')
        summaries = summaries_data.get('summaries') or summaries_data.get('papers', []) if summaries_data else []
        
        stats = {
            'papers_count': len(papers_data.get('papers', [])),
            'summaries_count': len(summaries),
            'knowledge_count': len(knowledge_data.get('papers', [])) if knowledge_data else 0,
            'knowledge_available': knowledge_data is not None,
            'analysis_available': analysis_data is not None,
            'last_update': papers_data.get('date') if papers_data else None
        }
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents')
def get_documents():
    """Return a filtered directory of policies, news, or industry reports."""
    try:
        source_type = str(request.args.get('source_type', '')).strip().lower()
        if source_type not in DIRECTORY_SOURCE_TYPES:
            return jsonify({
                'error': 'source_type 必须是 policy、news 或 industry_report'
                if language == 'zh'
                else 'source_type must be policy, news, or industry_report'
            }), 400

        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(100, max(1, request.args.get('per_page', 20, type=int)))
        priority = str(request.args.get('priority', '')).strip().lower()
        search = str(request.args.get('search', '')).strip().casefold()
        sort_by = str(request.args.get('sort', 'relevance')).strip().lower()

        documents = [
            relevance_ranker.rank_document(document)
            for document in _load_intelligence_documents()
            if str(document.get('source_type') or '').lower() == source_type
        ]
        if priority in {'high', 'medium', 'low'}:
            documents = [
                document for document in documents
                if document.get('reading_suggestion', {}).get('read_priority') == priority
            ]
        if search:
            documents = [
                document for document in documents
                if search in ' '.join(
                    str(value or '')
                    for value in (
                        document.get('title'),
                        document.get('summary'),
                        document.get('raw_text'),
                        ' '.join(document.get('authors_or_orgs') or []),
                        ' '.join(document.get('tags') or []),
                    )
                ).casefold()
            ]

        if sort_by == 'date':
            documents.sort(
                key=lambda item: str(item.get('published_at') or ''), reverse=True
            )
        elif sort_by == 'title':
            documents.sort(key=lambda item: str(item.get('title') or '').casefold())
        else:
            documents.sort(
                key=lambda item: float(item.get('importance_score') or 0), reverse=True
            )

        total = len(documents)
        start = (page - 1) * per_page
        return jsonify({
            'documents': documents[start:start + per_page],
            'source_type': source_type,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge')
def get_knowledge():
    """获取自适应结构化知识抽取结果"""
    try:
        knowledge_data = load_json('data/knowledge/latest.json')
        if not knowledge_data:
            return jsonify({'error': '没有找到结构化知识数据' if language == 'zh' else 'Knowledge data not found'}), 404
        return jsonify(knowledge_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/knowledge/papers/<paper_id>')
def get_paper_knowledge(paper_id):
    """获取单篇论文的结构化知识抽取结果"""
    try:
        knowledge_data = load_json('data/knowledge/latest.json')
        if not knowledge_data:
            return jsonify({'error': '没有找到结构化知识数据' if language == 'zh' else 'Knowledge data not found'}), 404
        for paper in knowledge_data.get('papers', []):
            if paper.get('id') == paper_id:
                return jsonify(paper)
        return jsonify({'error': t('error_paper_not_found')}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history')
def get_history():
    """获取历史趋势快照 / Get historical trend snapshots."""
    try:
        analysis_dir = project_root / 'data' / 'analysis'
        knowledge_dir = project_root / 'data' / 'knowledge'
        snapshots = {}

        for path in sorted(analysis_dir.glob('analysis_*.json')):
            data = load_json(str(path))
            if not data:
                continue
            date = data.get('date') or path.stem.replace('analysis_', '')
            snapshots.setdefault(date, {'date': date})
            snapshots[date]['paper_count'] = data.get('paper_count', 0)
            snapshots[date]['keywords'] = data.get('keywords', [])[:20]
            snapshots[date]['categories'] = data.get('statistics', {}).get('category_distribution', {})

        for path in sorted(knowledge_dir.glob('knowledge_*.json')):
            data = load_json(str(path))
            if not data:
                continue
            date = data.get('date') or path.stem.replace('knowledge_', '')
            snapshots.setdefault(date, {'date': date})
            taxonomy = data.get('taxonomy', {}).get('values', {})
            snapshots[date]['facet_counts'] = {
                facet: [
                    {'value': item.get('value'), 'count': item.get('count', 0)}
                    for item in values[:10]
                ]
                for facet, values in taxonomy.items()
            }

        history = sorted(snapshots.values(), key=lambda item: item.get('date', ''))
        return jsonify({'count': len(history), 'snapshots': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/images/<path:filename>')
def serve_image(filename):
    """提供图片文件"""
    analysis_dir = project_root / 'data' / 'analysis'
    return send_from_directory(str(analysis_dir), filename)


@app.route('/api/wordcloud')
def get_wordcloud():
    """获取词云图片路径"""
    try:
        analysis_data = load_json('data/analysis/latest.json')
        
        if not analysis_data:
            return jsonify({'error': t('error_no_analysis')}), 404
        
        wordcloud_path = analysis_data.get('wordcloud_path', '')
        
        # 转换为相对路径
        if wordcloud_path:
            filename = os.path.basename(wordcloud_path)
            wordcloud_url = f'/images/{filename}'
        else:
            wordcloud_url = None
        
        return jsonify({
            'url': wordcloud_url,
            'path': wordcloud_path
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return jsonify({'error': 'Internal server error'}), 500


def main():
    """运行 Web 服务"""
    host = web_config.get('host', '0.0.0.0')
    port = web_config.get('port', 5000)
    debug = web_config.get('debug', True)
    
    print("\n" + "=" * 60)
    print(f"🌐 {t('web_start')}")
    print("=" * 60)
    print(f"{t('access_url')}: http://localhost:{port}")
    print(f"{t('api_doc')}: http://localhost:{port}/api/stats")
    print("=" * 60)
    print(f"{t('stop_hint')}\n")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
