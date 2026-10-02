"""Keep publisher identity and original timestamps through document deduplication."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit


def policy_identity(document: dict) -> str:
    """Prefer an explicit policy number; extract its standard form when present."""
    if document.get('policy_number'):
        return str(document['policy_number']).strip()
    if document.get('source_type') != 'policy':
        return ''
    match = re.search(r'[\u4e00-\u9fff]{2,12}[〔\[（(]20\d{2}[〕\]）)]\s*\d+号',
                      str(document.get('title', '')) + str(document.get('raw_text', ''))[:500])
    return match[0] if match else ''


def source_identity(settings: dict, url: str = '') -> dict:
    host = (urlsplit(url or str(settings.get('url', ''))).hostname or '').lower()
    # Explicit owner_id is authoritative; known government/media subdomains share an owner.
    owner = next((root for root in ('people.com.cn', 'chinanews.com.cn', 'nea.gov.cn', 'ndrc.gov.cn', 'eeo.com.cn')
                  if host == root or host.endswith('.' + root)), host)
    return {
        'source_id': str(settings.get('source_id') or hashlib.sha256(str(settings.get('url') or host).encode()).hexdigest()[:16]),
        'owner_id': str(settings.get('owner_id') or owner),
        'owner_verified': bool(settings.get('owner_id') or owner in {'people.com.cn', 'chinanews.com.cn', 'nea.gov.cn', 'ndrc.gov.cn', 'eeo.com.cn'}),
        'tier': str(settings.get('tier') or ('T1' if host.endswith('.gov.cn') else 'T2')),
        'first_party': bool(settings.get('first_party', host.endswith('.gov.cn'))),
    }


def attach_observations(document: dict, config: dict) -> dict:
    """Attach one immutable observation, preserving any previously merged observations."""
    if not document.get('source_type') or not document.get('title'):
        return document
    provenance = document.setdefault('provenance', {})
    metadata = provenance.setdefault('metadata', {})
    if metadata.get('observations'):
        return document
    feed_url = provenance.get('fetch_url', '')
    settings = {}
    for source in config.get('sources', {}).values():
        if not isinstance(source, dict):
            continue
        for feed in [*source.get('feeds', []), *source.get('backfill_feeds', [])]:
            if feed.get('url') == feed_url:
                settings = feed
                break
    identity = source_identity(settings, feed_url or document.get('url', ''))
    if document.get('source_type') == 'paper':
        identity.update(tier='T1_5', first_party=True)
    published = str(document.get('published_at') or '')
    metadata['observations'] = [{
        **identity, 'document_id': str(document.get('id', '')),
        'origin_owner_id': metadata.get('origin_owner_id') or settings.get('origin_owner_id', ''),
        'source_name': document.get('source_name', ''), 'url': document.get('url', ''),
        'published_at': published, 'collected_at': document.get('collected_at', ''),
        'time_precision': 'time' if 'T' in published or ' ' in published else 'day' if len(published) == 10 else 'unknown',
    }]
    return document


def observations(document: dict) -> list[dict]:
    return document.get('provenance', {}).get('metadata', {}).get('observations', [])
