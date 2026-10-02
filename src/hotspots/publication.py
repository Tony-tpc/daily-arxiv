"""Read-only publication boundary shared by hotspot routes and the selected feed."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from .domain import allowed, content_key, recent, timestamp
from .store import HotspotStore


def publication(config: dict, documents: list[dict], *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if not config.get('hotspots', {}).get('enabled', False):
        return {'computed_at': None, 'boards': {'industry': [], 'academic': []}, 'details': {}, 'stale': False, 'reason': '热点功能未启用'}
    store = HotspotStore(config, readonly=True)
    payload = deepcopy(store.latest())
    completed = {row['id'] for row in store.documents() if row['editorial'].get('status') == 'complete'}
    admitted = {doc['id']: doc for doc in documents if allowed(doc, config)}
    hashes = {key: content_key(doc) for key, doc in admitted.items() if recent(doc, now)}
    visible = set(hashes) & completed
    details = {key: value for key, value in payload.get('details', {}).items()
               if set(value.get('document_ids', [])) <= visible and value.get('document_ids')
               and all(hashes.get(id) == digest for id, digest in value.get('document_hashes', {}).items())}
    # A changed admission removes the whole derived entry until recomputation, never stale counts.
    for detail in details.values():
        detail['background_documents'] = [{**ref, 'url': ''} for ref in detail.get('background_documents', [])
                                           if ref.get('id') in admitted]
    boards = {name: [entry for entry in payload.get('boards', {}).get(name, []) if entry['id'] in details]
              for name in ('industry', 'academic')}
    computed = timestamp(payload.get('computed_at'))
    return {**payload, 'details': details, 'boards': boards, 'computed_at': payload.get('computed_at'),
            'stale': bool(computed and now - computed > timedelta(hours=2)),
            'reason': '' if computed else '尚未生成热点；等待采集与精选任务完成'}


def selected_documents(config: dict, documents: list[dict], *, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    if not config.get('hotspots', {}).get('enabled', False):
        return []
    selected = {row['id']: row for row in HotspotStore(config, readonly=True).documents()
                if row['editorial'].get('selected') and row['editorial'].get('status') == 'complete'}
    result = []
    for doc in documents:
        row = selected.get(doc['id'])
        if row and allowed(doc, config) and recent(doc, now):
            if content_key(doc) == row['content_hash']:
                result.append({**doc, **{key: row['document'].get(key) for key in ('display_title', 'summary', 'research_topic', 'recommendation_reason', 'facts')},
                               'editorial': row['editorial'], 'hotspot_id': row['group_id']})
    return sorted(result, key=lambda item: (item.get('published_at', ''), item['id']), reverse=True)
