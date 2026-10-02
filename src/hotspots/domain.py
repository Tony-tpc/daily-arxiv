"""Shared admission, identity and original-time rules for jobs and public readers."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from src.academic_library import in_research_scope
from src.sources.paper_quality import is_high_impact_paper
from src.sources.policy_adapter import is_policy_in_scope
from src.sources.rss_adapter import is_news_in_scope

LOCAL_TZ = timezone(timedelta(hours=8))
INDUSTRY_WINDOW_DAYS = 7
ACADEMIC_WINDOW_DAYS = 180


def timestamp(value: object) -> datetime | None:
    text = str(value or '')
    if len(text) < 10:
        return None
    try:
        result = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return (result if result.tzinfo else result.replace(tzinfo=LOCAL_TZ)).astimezone(timezone.utc)
    except ValueError:
        return None


def allowed(document: dict, config: dict) -> bool:
    kind = document.get('source_type')
    title = str(document.get('title') or '')
    if not title or document.get('is_retracted'):
        return False
    if kind == 'paper':
        return is_high_impact_paper(document, config) and in_research_scope(document, config)
    if kind not in {'policy', 'news', 'industry_report'} or str(document.get('region') or 'CN').upper() != 'CN':
        return False
    exclusions = config.get('research_profile', {}).get('excluded_directions', [])
    if any(str(term).casefold() in title.casefold() for term in [*exclusions, '机械臂', '人形机器人', 'robot arm', 'humanoid']):
        return False
    if kind == 'policy':
        return is_policy_in_scope(document, config)
    if kind == 'news':
        settings = config.get('sources', {}).get('rss', {})
        include = settings.get('include_keywords', [])
        exclude = settings.get('exclude_keywords', [])
        return (is_news_in_scope(document, config)
                and (not include or any(str(term).casefold() in title.casefold() for term in include))
                and not any(str(term).casefold() in title.casefold() for term in exclude))
    return True


def recent(document: dict, now: datetime) -> bool:
    times = [timestamp(document.get('published_at'))]
    days = ACADEMIC_WINDOW_DAYS if document.get('source_type') == 'paper' else INDUSTRY_WINDOW_DAYS
    return any(at is not None and now - timedelta(days=days) < at <= now for at in times)


def content_key(document: dict) -> str:
    fields = ('title', 'raw_text', 'abstract', 'published_at', 'source_type', 'doi', 'authors_or_orgs')
    return fingerprint({key: document.get(key) for key in fields})


def fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def lexical_similarity(a: str, b: str) -> float:
    """AIHOT's shared character-bigram recall, not a semantic merge decision."""
    def grams(text):
        text = re.sub(r'\s+', '', text.casefold())
        return {text[i:i + 2] for i in range(len(text) - 1)}
    left, right = grams(a), grams(b)
    return len(left & right) / min(len(left), len(right)) if left and right else 0.0


def strong_identity(document: dict) -> tuple[str, str]:
    from src.sources.observations import policy_identity
    if document.get('doi'):
        return 'doi', str(document['doi']).strip().lower().removeprefix('https://doi.org/')
    if document.get('arxiv_id'):
        return 'arxiv', re.sub(r'v\d+$', '', str(document['arxiv_id']).strip().lower())
    number = policy_identity(document)
    if number:
        return 'policy', str(number)
    return 'url', str(document.get('canonical_url') or document.get('url') or '')
