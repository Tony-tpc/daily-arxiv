"""工具函数模块"""
import copy
import os
import yaml
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return normalize_config(config)


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize config to the new multi-source shape while preserving compatibility."""
    normalized = copy.deepcopy(config or {})

    sources = normalized.setdefault('sources', {})
    legacy_arxiv = normalized.get('arxiv')
    source_arxiv = sources.get('arxiv')

    if isinstance(legacy_arxiv, dict) and not isinstance(source_arxiv, dict):
        sources['arxiv'] = copy.deepcopy(legacy_arxiv)
    elif isinstance(source_arxiv, dict) and not isinstance(legacy_arxiv, dict):
        normalized['arxiv'] = copy.deepcopy(source_arxiv)

    normalized.setdefault('tracking_topics', [])
    normalized.setdefault('regional_focus', ['CN'])
    normalized.setdefault('keyword_groups', [])
    normalized.setdefault('negative_keywords', [])
    normalized.setdefault('priority_rules', [])

    research_profile = normalized.setdefault('research_profile', {})
    research_profile.setdefault('topic', '')
    research_profile.setdefault('focus', [])
    research_profile.setdefault('excluded_directions', [])

    tag_extraction = normalized.setdefault('tag_extraction', {})
    tag_extraction.setdefault('enabled', True)
    tag_extraction.setdefault('include_configured_topics', True)
    tag_extraction.setdefault('max_tags', 20)
    tag_extraction.setdefault('max_entities', 30)

    ranking_config = normalized.setdefault('ranking', {})
    ranking_config.setdefault('enabled', True)
    ranking_config.setdefault('weights', copy.deepcopy({
        'topic_relevance': 0.40,
        'novelty': 0.15,
        'policy_importance': 0.20,
        'industry_relevance': 0.15,
        'source_credibility': 0.10,
    }))
    ranking_config.setdefault('thresholds', {'high': 70, 'medium': 45})

    linking_config = normalized.setdefault('linking', {})
    linking_config.setdefault('enabled', True)
    linking_config.setdefault('title_similarity_threshold', 0.92)
    linking_config.setdefault('relation_threshold', 0.35)
    linking_config.setdefault('max_related_per_document', 8)

    outputs = normalized.setdefault('outputs', {})
    outputs.setdefault('markdown', {'enabled': True, 'directory': 'data/markdown'})
    outputs.setdefault('json', {'enabled': True, 'directory': 'data'})
    outputs.setdefault('obsidian', {'enabled': False, 'vault_path': 'data/obsidian'})
    outputs.setdefault('zotero', {'enabled': False, 'mode': 'local_api'})

    analysis = normalized.setdefault('analysis', {})
    analysis.setdefault('trend_window_days', [7, 30, 60])
    analysis.setdefault('compare_sources', True)
    analysis.setdefault('entity_tracking', True)

    for source_name in ['arxiv', 'openalex', 'openalex_search', 'rss', 'policy', 'industry_report']:
        source_config = sources.setdefault(source_name, {})
        if isinstance(source_config, dict):
            source_config.setdefault('enabled', source_name in ('arxiv', 'openalex'))

    arxiv_config = sources.setdefault('arxiv', {})
    if isinstance(arxiv_config, dict):
        ranking = arxiv_config.setdefault('ranking', {})
        if isinstance(ranking, dict):
            ranking.setdefault('enabled', True)
            ranking.setdefault('primary', 'citation_count')
            ranking.setdefault('secondary', 'openalex_referenced_works_count')

    openalex_config = sources.setdefault('openalex', {})
    if isinstance(openalex_config, dict):
        openalex_config.setdefault('api_key', '')
        openalex_config.setdefault('email', '')
        if not openalex_config.get('api_key'):
            openalex_config['api_key'] = os.getenv('OPENALEX_API_KEY', '')
        if not openalex_config.get('email'):
            openalex_config['email'] = os.getenv('OPENALEX_EMAIL', '')
        openalex_config.setdefault('per_page', 25)
        openalex_config.setdefault('request_timeout_seconds', 20)
        openalex_config.setdefault('max_title_search_results', 5)
        openalex_config.setdefault('cache_path', 'data/cache/openalex_works.json')
        openalex_config.setdefault(
            'select_fields',
            [
                'id',
                'doi',
                'title',
                'display_name',
                'publication_year',
                'cited_by_count',
                'primary_topic',
                'topics',
                'authorships',
                'referenced_works',
                'referenced_works_count',
                'ids',
                'updated_date',
            ],
        )

    openalex_search_config = sources.setdefault('openalex_search', {})
    if isinstance(openalex_search_config, dict):
        openalex_search_config.setdefault('enabled', False)
        openalex_search_config.setdefault('request_timeout_seconds', 20)
        openalex_search_config.setdefault('per_page', 25)
        openalex_search_config.setdefault('max_results', 20)
        openalex_search_config.setdefault('recent_days', 180)

    rss_config = sources.setdefault('rss', {})
    if isinstance(rss_config, dict):
        rss_config.setdefault('feeds', [])
        rss_config.setdefault('request_timeout_seconds', 20)
        rss_config.setdefault('state_path', 'data/state/rss.json')
        rss_config.setdefault('snapshot_dir', 'data/raw/rss')
        rss_config.setdefault('max_entries_per_feed', 100)
        rss_config.setdefault('max_seen_items', 10000)

    policy_config = sources.setdefault('policy', {})
    if isinstance(policy_config, dict):
        policy_config.setdefault('feeds', [])
        policy_config.setdefault('request_timeout_seconds', 20)
        policy_config.setdefault('state_path', 'data/state/policy.json')
        policy_config.setdefault('snapshot_dir', 'data/raw/policy')
        policy_config.setdefault('max_entries_per_feed', 100)
        policy_config.setdefault('max_seen_items', 10000)
        policy_config.setdefault('llm_extraction', {'enabled': True, 'max_tokens': 900})

    industry_config = sources.setdefault('industry_report', {})
    if isinstance(industry_config, dict):
        industry_config.setdefault('feeds', [])
        industry_config.setdefault('request_timeout_seconds', 20)
        industry_config.setdefault('state_path', 'data/state/industry_report.json')
        industry_config.setdefault('snapshot_dir', 'data/raw/industry_report')
        industry_config.setdefault('max_entries_per_feed', 100)
        industry_config.setdefault('max_seen_items', 10000)
        industry_config.setdefault('llm_extraction', {'enabled': True, 'max_tokens': 900})

    if isinstance(normalized.get('arxiv'), dict):
        normalized['arxiv'].setdefault('enabled', True)

    return normalized


def load_env():
    """加载环境变量"""
    load_dotenv()


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """设置日志
    
    Args:
        config: 配置字典
        
    Returns:
        Logger 对象
    """
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建 logger
    logger = logging.getLogger('daily_arxiv')
    logger.setLevel(log_level)
    
    # 控制台处理器
    if log_config.get('console', True):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(console_handler)
    
    # 文件处理器
    log_file = log_config.get('file')
    if log_file:
        # 确保日志目录存在
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)
    
    return logger


def save_json(data: Any, filepath: str):
    """保存 JSON 数据
    
    Args:
        data: 要保存的数据
        filepath: 文件路径
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(filepath: str) -> Any:
    """加载 JSON 数据
    
    Args:
        filepath: 文件路径
        
    Returns:
        加载的数据
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_date_string(date: Optional[datetime] = None) -> str:
    """获取日期字符串
    
    Args:
        date: datetime 对象，默认为当前日期
        
    Returns:
        格式化的日期字符串 YYYY-MM-DD
    """
    if date is None:
        date = datetime.now()
    return date.strftime('%Y-%m-%d')


def get_data_path(config: Dict[str, Any], subdir: str = 'papers') -> str:
    """获取数据存储路径
    
    Args:
        config: 配置字典
        subdir: 子目录名称
        
    Returns:
        数据路径
    """
    storage_config = config.get('storage', {})
    base_path = storage_config.get('json_path', 'data/papers')
    
    if subdir in {'summaries', 'documents'}:
        return f'data/{subdir}'
    
    return base_path


def get_language(config: Dict[str, Any]) -> str:
    """Get deployment language.

    Returns:
        'en' for English mode, otherwise 'zh'
    """
    app_config = config.get('app', {}) if isinstance(config, dict) else {}
    language = str(app_config.get('language', 'zh')).strip().lower()
    return 'en' if language.startswith('en') else 'zh'


def pick_text(config: Dict[str, Any], zh_text: str, en_text: str) -> str:
    """Pick localized text using deployment language."""
    return en_text if get_language(config) == 'en' else zh_text
