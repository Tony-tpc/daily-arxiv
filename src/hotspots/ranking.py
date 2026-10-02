"""Deterministic event attention and academic activity; no models or network calls."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from src.sources.observations import observations, source_identity
from src.utils import load_json

from .domain import allowed, fingerprint, recent, timestamp
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
    for row in rows:
        for observation in observations(row['document']):
            published = timestamp(observation.get('published_at'))
            owner = observation.get('owner_id')
            if not owner or not published or not at - timedelta(hours=48) < published <= at:
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
    """Publish all detail and board data together; an empty board is a valid result."""
    now = now or datetime.now(timezone.utc)
    store = store or HotspotStore(config)
    sources = {row['id']: json.loads(row['payload']) for row in store.rows('SELECT * FROM sources')}
    audits = {row['key']: json.loads(row['payload']) for row in store.rows('SELECT * FROM audits')}
    groups = {row['id']: row for row in store.rows('SELECT * FROM groups')}
    digests = {row['id']: row for row in store.rows('SELECT * FROM digests')}
    grouped = {}
    for row in store.documents():
        if row['group_id'] and row['editorial'].get('status') == 'complete' and row['editorial'].get('selected') and allowed(row['document'], config):
            grouped.setdefault(row['group_id'], []).append(row)
    entries = {'industry': [], 'academic': []}
    details = {}
    for group_id, rows in grouped.items():
        group = groups.get(group_id)
        if not group:
            continue
        kind = group['kind']
        active = [row for row in rows if recent(row['document'], now)]
        if not active:
            continue
        # A database provider is never an independent academic contribution.
        if kind == 'academic':
            unique = {}
            for row in active:
                doc = row['document']
                identity = str(doc.get('doi') or doc.get('arxiv_id') or doc['id']).lower().removeprefix('https://doi.org/')
                unique.setdefault(identity, row)
            active = list(unique.values())
            score = sum(0.5 ** ((now - timestamp(row['document']['published_at'])).total_seconds() / (15 * 86400)) for row in active)
            institutions = sorted({str(value) for row in active for value in row['document'].get('openalex_institutions', []) if value})
            count = len(active)
            source_count = 0
            coverage = {'complete': False, 'reason': '学术库按周采集；活跃度不表示全领域统计或实时增长'}
            trend, change = 'unknown', None
        else:
            current = _participants(rows, now)
            previous = _participants(rows, now - timedelta(hours=6))
            score, count, source_count = _heat(current, now), len(current), len(current)
            institutions = []
            cohort = {}
            for owner in current.keys() | previous.keys():
                ids = current.get(owner, {}).get('sources', set()) | previous.get(owner, {}).get('sources', set())
                if ids and all(_clock_ok(sources.get(sid, {}), now)
                               and (timestamp(sources.get(sid, {}).get('since')) or now) <= now - timedelta(hours=54) for sid in ids):
                    cohort[owner] = True
            complete = bool(current) and all(_clock_ok(sources.get(sid, {}), now) for item in current.values() for sid in item['sources'])
            coverage = {'complete': complete, 'reason': '' if complete else '部分来源采集不完整，暂无可比趋势'}
            prev = _heat({key: value for key, value in previous.items() if key in cohort}, now - timedelta(hours=6))
            cur = _heat({key: value for key, value in current.items() if key in cohort}, now)
            change = round((cur - prev) / prev * 100, 1) if prev > 0 and complete else None
            trend = 'unknown' if change is None else 'up' if change > 10 else 'down' if change < -10 else 'flat'
        representative = sorted(active, key=lambda row: (not any(o.get('first_party') for o in observations(row['document'])),
                                 -float(row['editorial'].get('score', 0)), row['id']))[0]
        doc = representative['document']
        digest_row = digests.get(group_id, {})
        digest_inputs = [{key: row['document'].get(key) for key in ('id', 'title', 'summary', 'published_at')} for row in sorted(active, key=lambda row: row['id'])]
        digest = json.loads(digest_row['payload']) if digest_row.get('input_hash') == fingerprint(digest_inputs) else {}
        evidence = []
        for row in sorted(active, key=lambda row: row['document'].get('published_at', ''), reverse=True):
            item = row['document']
            audit = audits.get(audit_key(item), {})
            evidence.append({key: item.get(key) for key in ('id', 'title', 'display_title', 'source_type', 'source_name', 'published_at', 'summary')}
                            | {'url': audit.get('final_url') or item.get('url', '') if audit.get('status') == 'verified' else '',
                               'link_status': audit.get('status', 'unverified'),
                               'observations': [{'source_name': o.get('source_name'), 'published_at': o.get('published_at'), 'owner_id': o.get('owner_id')} for o in observations(item)]})
        exact_times = [timestamp(o.get('published_at')) for row in active for o in observations(row['document']) if o.get('time_precision') == 'time']
        first_times = [timestamp(row['document'].get('published_at')) for row in rows]
        first = min((value for value in first_times if value), default=now)
        entry = {
            'id': group_id, 'kind': kind, 'title': group['title'], 'score': round(score, 6),
            'paper_count': len(active) if kind == 'academic' else 0, 'source_count': source_count,
            'institution_count': len(institutions), 'institutions': institutions, 'report_count': len(active),
            'summary': digest.get('summary') or doc.get('summary', ''), 'summary_kind': 'digest' if digest else 'representative',
            'trend': trend, 'trend_pct': change,
            'is_new': kind == 'industry' and first in exact_times and timedelta(0) <= now - first < timedelta(hours=6),
            'coverage': coverage, 'latest_at': max(row['document'].get('published_at', '') for row in active),
            'document_ids': [row['id'] for row in active],
            'document_hashes': {row['id']: row['content_hash'] for row in active},
            'selection_score': sum(float(row['editorial'].get('score', 0)) for row in active) / len(active),
        }
        details[group_id] = {**entry, 'evidence': evidence, 'timeline': evidence, 'series': [],
                             'background_documents': list({ref['id']: ref for row in active for ref in row['document'].get('related_documents', []) if ref.get('id') and (ref.get('source_type') == 'paper') != (kind == 'academic')}.values())}
        if count >= 2:
            entries[kind].append(entry)
    for board in entries:
        entries[board].sort(key=lambda entry: (-entry['score'], -entry['institution_count'], -entry['selection_score'], entry['id']))
        entries[board] = [{**entry, 'rank': rank} for rank, entry in enumerate(entries[board][:10], 1)]
    previous = store.rows('SELECT hour,payload FROM snapshots WHERE hour>=? ORDER BY hour', ((now - timedelta(days=30)).isoformat(),))
    for row in previous:
        if timestamp(row['hour']) >= now.replace(minute=0, second=0, microsecond=0):
            continue
        for group_id, detail in json.loads(row['payload']).get('details', {}).items():
            if group_id in details:
                details[group_id]['series'].append({'at': row['hour'], 'score': detail['score'] if detail['coverage']['complete'] else None})
    for detail in details.values():
        detail['series'].append({'at': now.isoformat(), 'score': detail['score'] if detail['coverage']['complete'] else None})
        detail['series'] = detail['series'][-168:]
    payload = {'computed_at': now.isoformat(), 'rule_version': 'energy-hotspots-v1', 'boards': entries, 'details': details}
    with store.connect() as db:
        db.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?)', (now.replace(minute=0, second=0, microsecond=0).isoformat(), json.dumps(payload, ensure_ascii=False)))
        db.execute('DELETE FROM snapshots WHERE hour<?', ((now - timedelta(days=30)).isoformat(),))
    return payload
