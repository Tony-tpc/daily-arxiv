"""Deterministic event attention and academic activity; no models or network calls."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from src.sources.observations import observations, source_identity
from src.utils import load_json

from .domain import INDUSTRY_WINDOW_DAYS, allowed, fingerprint, lexical_similarity, recent, timestamp
from .store import HotspotStore


def record_source_health(store: HotspotStore, config: dict, now: datetime) -> None:
    """Read durable collector clocks, not scheduler success, including individual failures."""
    previous = {row['id']: json.loads(row['payload']) for row in store.rows('SELECT * FROM sources')}
    for name, settings in config.get('sources', {}).items():
        if not isinstance(settings, dict) or not settings.get('enabled', False):
            continue
        state = load_json(settings.get('state_path', f'data/state/{name}.json')) or {}
        hours = {'rss': 8, 'policy': 24, 'industry_report': 168}.get(name, 168)
        for feed in settings.get('feeds', []):
            if not feed.get('enabled', True):
                continue
            identity = source_identity(feed)
            old = previous.get(identity['source_id'], {})
            clock = state.get('feeds', {}).get(feed.get('url'), {})
            value = {**identity, 'since': old.get('since', now.isoformat()), 'name': feed.get('name', ''),
                     'last_success_at': clock.get('last_success_at'), 'error': clock.get('last_error', ''), 'interval_hours': hours}
            store.execute('INSERT OR REPLACE INTO sources VALUES (?,?)', (identity['source_id'], json.dumps(value, ensure_ascii=False)))


def _participants(rows: list[dict], at: datetime) -> dict:
    participants = {}
    seen_text = set()
    for row in rows:
        doc = row['document']
        if doc.get('source_type') == 'paper':
            continue
        text = ''.join(str(doc.get('raw_text') or '').split())
        if text and any(text == old or lexical_similarity(text, old) >= .95 for old in seen_text):
            continue
        seen_text.add(text)
        # A merged title observation without its own body cannot establish an
        # independent report. Keep all observations for audit, count the actual body.
        own = [o for o in observations(doc) if o.get('url') == doc.get('url')]
        for observation in (own or observations(doc)[:1]):
            published = timestamp(observation.get('published_at'))
            owner = observation.get('origin_owner_id') or observation.get('owner_id')
            verified = (observation.get('origin_owner_id') or observation.get('owner_verified') or
                        owner in {'people.com.cn', 'chinanews.com.cn', 'nea.gov.cn', 'ndrc.gov.cn', 'eeo.com.cn'})
            if not verified or not owner or not published or not at - timedelta(days=INDUSTRY_WINDOW_DAYS) < published <= at:
                continue
            current = participants.setdefault(owner, {'at': published, 'sources': set(), 'observations': []})
            current['at'] = max(current['at'], published)
            current['sources'].add(observation.get('source_id'))
            current['observations'].append(observation)
    return participants


def _heat(participants: dict, at: datetime) -> float:
    return 10 * sum(0.5 ** ((at - value['at']).total_seconds() / 86400) for value in participants.values())


def _clock_ok(clock: dict, now: datetime) -> bool:
    last = timestamp(clock.get('last_success_at'))
    return bool(last and not clock.get('error') and last >= now - timedelta(hours=max(1.5, float(clock.get('interval_hours', 8)) * 3)))


def audit_key(document: dict) -> str:
    return fingerprint([document.get('url'), document.get('title')])


def recompute(config: dict, *, now: datetime | None = None, store: HotspotStore | None = None) -> dict:
    """Atomically publish only completed, cross-evidence topic analyses."""
    from .topics import RULE_VERSION, member_key, profiles, topics, unique_members
    now = now or datetime.now(timezone.utc)
    store = store or HotspotStore(config)
    records = profiles(store)
    grouped = {}
    progress = {kind: {'eligible_documents': 0, 'ready_documents': 0, 'pending_documents': 0,
                       'awaiting_content': 0, 'blocked_documents': 0, 'source_count': 0,
                       'candidate_topics': 0, 'analyzing_topics': 0, 'failed_topics': 0,
                       'largest_topic_documents': 0, 'largest_topic_sources': 0,
                       'failed_sources': []} for kind in ('industry', 'academic')}
    owners = set()
    for row in records:
        doc = row['document']
        if not allowed(doc, config) or not recent(doc, now):
            continue
        kind = 'academic' if doc['source_type'] == 'paper' else 'industry'
        progress[kind]['eligible_documents'] += 1
        bucket = {'complete': 'ready_documents', 'pending': 'pending_documents',
                  'awaiting_content': 'awaiting_content', 'blocked': 'blocked_documents'}.get(row['status'], 'pending_documents')
        progress[kind][bucket] += 1
        if row['status'] == 'complete' and row['topic_id']:
            grouped.setdefault(row['topic_id'], []).append(row)
            if kind == 'industry':
                owners.update(_participants([row], now))
    progress['industry']['source_count'] = len(owners)
    source_rows = [json.loads(r['payload']) for r in store.rows('SELECT payload FROM sources')]
    progress['industry']['failed_sources'] = [{'name': r.get('name', ''), 'error': r['error']}
                                            for r in source_rows if r.get('error')]
    audits = {r['key']: json.loads(r['payload']) for r in store.rows('SELECT * FROM audits')}
    selected = {r['id']: r['editorial'] for r in store.documents()}
    previous = store.latest().get('details', {})
    boards, details = {'industry': [], 'academic': []}, {}
    for topic in topics(store):
        kind, rows = topic['kind'], grouped.get(topic['id'], [])
        rows = unique_members(rows)
        if not rows:
            continue
        progress[kind]['candidate_topics'] += 1
        participants = _participants(rows, now) if kind == 'industry' else {}
        progress[kind]['largest_topic_documents'] = max(progress[kind]['largest_topic_documents'], len(rows))
        progress[kind]['largest_topic_sources'] = max(progress[kind]['largest_topic_sources'], len(participants))
        if len(rows) < 2 or (kind == 'industry' and len(participants) < 2):
            continue
        if topic['input_hash'] != member_key(rows, RULE_VERSION) or not topic['analysis']:
            progress[kind]['failed_topics' if topic['error'] else 'analyzing_topics'] += 1
            old = previous.get(topic['id'], {})
            if (not old.get('analysis') or old.get('document_hashes') != {r['id']: r['content_hash'] for r in rows}):
                continue
        analysis = topic['analysis']
        institutions = sorted({str(i) for r in rows for i in r['document'].get('openalex_institutions', []) if i}) if kind == 'academic' else []
        score = (_heat(participants, now) if kind == 'industry' else
                 sum(0.5 ** ((now - timestamp(r['document']['published_at'])).total_seconds() / (15 * 86400)) for r in rows))
        evidence = []
        for row in sorted(rows, key=lambda r: r['document'].get('published_at', ''), reverse=True):
            doc = row['document']; audit = audits.get(audit_key(doc), {})
            evidence.append({k: doc.get(k) for k in ('id', 'title', 'display_title', 'source_type', 'source_name', 'published_at', 'summary')}
                            | {'url': (audit.get('final_url') or doc.get('url', '')) if audit.get('status') == 'verified' else '',
                               'link_status': audit.get('status', 'unverified'), 'event': row['profile'].get('event', {}),
                               'doi': doc.get('doi', ''), 'original_text': doc.get('abstract') or doc.get('raw_text') or '',
                               'observations': observations(doc)})
        entry = {'id': topic['id'], 'kind': kind, 'analysis_type': 'research_problem' if kind == 'academic' else 'industry_issue',
                 'analysis_status': 'complete',
                 'title': analysis.get('title') or topic['definition']['title'], 'summary': analysis['summary'], 'summary_kind': 'analysis',
                 'analysis': analysis, 'score': round(score, 6), 'paper_count': len(rows) if kind == 'academic' else 0,
                 'source_count': len(participants), 'report_count': len(rows), 'institution_count': len(institutions),
                 'institutions': institutions, 'document_ids': [r['id'] for r in rows],
                 'document_hashes': {r['id']: r['content_hash'] for r in rows}, 'is_new': False,
                 'selection_score': sum(float(selected.get(r['id'], {}).get('score', 0)) for r in rows) / len(rows),
                 'latest_at': max(r['document']['published_at'] for r in rows), 'trend': 'unknown', 'trend_pct': None,
                 'coverage': {'complete': False, 'reason': '仅覆盖本地准入资料；缺乏完整可比采集历史，不宣称全领域热度或增长'}}
        months = {}
        for row in rows:
            month = row['document']['published_at'][:7]
            months[month] = months.get(month, 0) + 1
        details[topic['id']] = {**entry, 'evidence': evidence, 'timeline': evidence, 'series': [],
                                'publication_distribution': [{'month': m, 'count': n} for m, n in sorted(months.items())],
                                'background_documents': []}
        boards[kind].append(entry)
    for kind in boards:
        boards[kind].sort(key=lambda e: (-e['score'], -e['institution_count'], -e['selection_score'], e['id']))
        boards[kind] = [{**e, 'rank': i} for i, e in enumerate(boards[kind][:10], 1)]
    payload = {'computed_at': now.isoformat(), 'rule_version': RULE_VERSION, 'boards': boards,
               'details': details, 'processing': progress}
    with store.connect() as db:
        db.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?)',
                   (now.replace(minute=0, second=0, microsecond=0).isoformat(), json.dumps(payload, ensure_ascii=False)))
        db.execute('DELETE FROM snapshots WHERE hour<?', ((now - timedelta(days=30)).isoformat(),))
    return payload
