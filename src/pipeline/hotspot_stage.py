"""Audit public links offline and publish a consistent snapshot after writing summaries."""
import json
from datetime import datetime, timezone

from src.hotspots.domain import allowed, recent
from src.hotspots.ranking import audit_key, recompute
from src.hotspots.store import HotspotStore
from src.verification.evidence_link_audit import audit_evidence_index


def run(context):
    if not context.config.get('hotspots', {}).get('enabled', False):
        return context
    store = HotspotStore(context.config)
    now = datetime.now(timezone.utc)
    if context.config.get('verification', {}).get('evidence_links', {}).get('enabled', True):
        cached = {row['key'] for row in store.rows('SELECT key FROM audits')}
        from src.hotspots.topics import profiles
        documents = [row['document'] for row in profiles(store) if row['status'] == 'complete']
        index = {audit_key(doc): {**doc, 'document_id': doc['id']} for doc in documents
                 if allowed(doc, context.config) and recent(doc, now) and audit_key(doc) not in cached}
        if index:
            for key, audit in audit_evidence_index(index).items():
                store.execute('INSERT OR REPLACE INTO audits VALUES (?,?)', (key, json.dumps(audit, ensure_ascii=False)))
    recompute(context.config, store=store, now=now)
    return context
