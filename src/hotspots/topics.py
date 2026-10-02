"""Evidence-backed problem/issue analysis, independent of editorial selection."""
from __future__ import annotations

import json
import math
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.sources.observations import attach_observations
from .domain import allowed, content_key, fingerprint, lexical_similarity, recent, strong_identity
from .store import HotspotStore

RULE_VERSION = 'energy-topic-analysis-v2'
SECTION_KEYS = {
    'academic': ['question', 'attention', 'methods', 'progress', 'limitations', 'next_steps'],
    'industry': ['events', 'changes', 'drivers', 'impacts', 'uncertainty', 'watchpoints'],
}


def validate_response(namespace: str, result: dict, payload: dict) -> None:
    """Validate before caching so a malformed answer never poisons durable retries."""
    if namespace == 'analysis_profile':
        if result.get('decision') not in {'PASS', 'BLOCK', 'UNKNOWN'}:
            raise ValueError('研究画像缺少领域判断')
        if result['decision'] == 'PASS' and not all(isinstance(result.get(k), str) and result[k].strip()
                                                     for k in ('title', 'system', 'problem', 'definition')):
            raise ValueError('研究画像缺少主题边界')
    elif namespace.startswith('analysis_match:'):
        confidence = float(result.get('confidence', -1))
        ids = {row['id'] for row in payload['candidates']}
        if not math.isfinite(confidence) or not 0 <= confidence <= 1 or result.get('topic_id') not in ids | {None}:
            raise ValueError('主题匹配结果无效')
    elif namespace == 'analysis_synthesis':
        ids = {row['id'] for row in payload['documents']}
        sections = result.get('sections', [])
        def valid_refs(refs):
            return isinstance(refs, list) and bool(refs) and all(isinstance(ref, str) and ref in ids for ref in refs)
        if (not isinstance(result.get('summary'), str) or not result['summary'].strip()
                or not valid_refs(result.get('evidence_ids')) or len(set(result['evidence_ids'])) < 2
                or not isinstance(sections, list) or not all(isinstance(s, dict) for s in sections)
                or [s.get('key') for s in sections] != SECTION_KEYS[payload['kind']]):
            raise ValueError('综合分析缺少完整结构或跨资料引用')
        for section in sections:
            if (not isinstance(section.get('text'), str) or not section['text'].strip()
                    or not isinstance(section.get('title'), str) or not section['title'].strip()
                    or section.get('kind') not in {'fact', 'inference', 'question'}
                    or not valid_refs(section.get('evidence_ids'))):
                raise ValueError('分析段落或引用无效')
    elif namespace == 'analysis_review':
        if not isinstance(result.get('supported'), bool):
            raise ValueError('分析核验结论无效')


def profiles(store: HotspotStore) -> list[dict]:
    # Older read-only stores may not have been migrated by a writer yet.
    if not store.rows("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_profiles'"):
        return []
    return [{**row, 'document': json.loads(row['document']), 'profile': json.loads(row['profile'])}
            for row in store.rows('SELECT * FROM analysis_profiles ORDER BY id')]


def topics(store: HotspotStore) -> list[dict]:
    if not store.rows("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_topics'"):
        return []
    return [{**row, 'definition': json.loads(row['definition']), 'analysis': json.loads(row['analysis'])}
            for row in store.rows('SELECT * FROM analysis_topics ORDER BY id')]


def member_key(rows: list[dict], version: str) -> str:
    return fingerprint([version, sorted((r['id'], r['content_hash'], r['version']) for r in rows)])


def unique_members(rows: list[dict]) -> list[dict]:
    """Use the same identity boundary when synthesizing and publishing."""
    unique = {}
    for row in rows:
        doc = row['document']
        identity = strong_identity(doc)
        if not identity[1]:
            identity = ('id', row['id'])
        unique.setdefault(identity, row)
    return list(unique.values())


def source_text(doc: dict) -> str:
    return str(doc.get('abstract') or doc.get('raw_text') or '').strip()


class TopicEngine:
    def __init__(self, config: dict, client, *, now: datetime | None = None):
        self.config, self.client = config, client
        self.now = now or datetime.now(timezone.utc)
        self.store = HotspotStore(config)
        prompt_dir = Path(__file__).with_name('prompts')
        self.version = fingerprint([RULE_VERSION, client.route, client.model,
                                   [(p.name, p.read_text(encoding='utf-8')) for p in sorted(prompt_dir.glob('analysis_*.md'))]])

    def save(self, doc, profile, status, topic_id=None, error=''):
        self.store.execute('INSERT OR REPLACE INTO analysis_profiles VALUES (?,?,?,?,?,?,?,?)',
                           (doc['id'], content_key(doc), self.version, json.dumps(doc, ensure_ascii=False),
                            json.dumps(profile, ensure_ascii=False), status, topic_id, error))

    def process(self, documents: list[dict]) -> None:
        indexed = {r['id']: r for r in profiles(self.store)}
        # The pipeline passes the merged current library; an empty input resumes durable work.
        inputs = documents or [r['document'] for r in indexed.values()]
        seen = set()
        for incoming in sorted(inputs, key=lambda d: str(d.get('id', ''))):
            doc = attach_observations(dict(incoming), self.config)
            aliases = [str(key) for key in doc.get('duplicate_document_ids', []) if key != doc.get('id')]
            for alias in aliases:
                self.store.execute('DELETE FROM analysis_profiles WHERE id=?', (alias,))
            if not doc.get('id') or not allowed(doc, self.config) or not recent(doc, self.now):
                if doc.get('id'):
                    self.store.execute('DELETE FROM analysis_profiles WHERE id=?', (doc['id'],))
                continue
            identity = strong_identity(doc) if doc.get('source_type') == 'paper' else ('document', doc['id'])
            if identity in seen:
                continue
            seen.add(identity)
            old = indexed.get(doc['id'])
            unchanged = old and old['content_hash'] == content_key(doc) and old['version'] == self.version
            if unchanged and old['status'] in {'complete', 'blocked', 'awaiting_content'}:
                self.save(doc, old['profile'], old['status'], old['topic_id'])
                continue
            if len(source_text(doc)) < 100:
                self.save(doc, {}, 'awaiting_content')
                continue
            if not self.client.claim_document(doc['id']) or self.client.calls >= self.client.limit:
                if old and old['status'] == 'complete' and old['content_hash'] == content_key(doc):
                    self.store.execute('UPDATE analysis_profiles SET error=? WHERE id=?', ('新版本分析等待预算', doc['id']))
                else:
                    self.save(doc, old['profile'] if unchanged else {}, 'pending')
                continue
            try:
                kind = 'academic' if doc['source_type'] == 'paper' else 'industry'
                material = {k: doc.get(k) for k in ('id', 'title', 'source_type', 'published_at', 'doi')}
                material.update(kind=kind, text=source_text(doc)[:14000])
                profile = self.client.ask('analysis_profile', material, 'analysis_profile')
                if profile['decision'] != 'PASS':
                    self.save(doc, profile, 'blocked' if profile['decision'] == 'BLOCK' else 'awaiting_content')
                    continue
                topic_id = self.assign(doc, profile, kind)
                self.save(doc, profile, 'complete', topic_id)
                logging.getLogger('daily_arxiv').info('主题画像完成：%s → %s', doc['title'][:65], topic_id)
            except Exception as exc:
                if old and old['status'] == 'complete' and old['content_hash'] == content_key(doc):
                    self.store.execute('UPDATE analysis_profiles SET error=? WHERE id=?', (str(exc), doc['id']))
                else:
                    self.save(doc, old['profile'] if unchanged else {}, 'pending', error=str(exc))
        self.synthesize()

    def assign(self, doc: dict, profile: dict, kind: str) -> str:
        text = profile['system'] + profile['problem'] + profile['definition']
        memberships = {}
        for row in profiles(self.store):
            if row['status'] == 'complete' and row['topic_id']:
                memberships.setdefault(row['topic_id'], set()).add(row['id'])
        # A singleton's exact copy of this paper is not an independent candidate
        # problem. Excluding it prevents self-matches from defeating regrouping.
        candidates = [r for r in topics(self.store) if r['kind'] == kind
                      and memberships.get(r['id'], set()) - {doc['id']}]
        candidates.sort(key=lambda r: (-lexical_similarity(text, json.dumps(r['definition'], ensure_ascii=False)), r['id']))
        candidates = [{'id': r['id'], 'definition': {k: r['definition'].get(k, '')
                      for k in ('title', 'system', 'problem', 'definition')}} for r in candidates[:10]]
        # A retry of the same seed preserves its original ID without accumulating orphan groups.
        topic_id = kind + '-' + fingerprint([RULE_VERSION, kind, doc['id']])[:20]
        if candidates:
            payload = {'kind': kind, 'profile': {k: profile.get(k, '') for k in ('title', 'system', 'problem', 'definition')}, 'candidates': candidates}
            first = self.client.ask('analysis_match', payload, 'analysis_match:primary')
            if first.get('topic_id') and first['confidence'] >= 0.8:
                second = self.client.ask('analysis_match', payload, 'analysis_match:review')
                if second.get('topic_id') == first['topic_id'] and second['confidence'] >= 0.8:
                    return first['topic_id']
        self.store.execute('INSERT OR IGNORE INTO analysis_topics (id,kind,definition) VALUES (?,?,?)',
                           (topic_id, kind, json.dumps(profile, ensure_ascii=False)))
        return topic_id

    def synthesize(self) -> None:
        from .ranking import _participants
        grouped = {}
        for row in profiles(self.store):
            if (row['status'] == 'complete' and row['version'] == self.version and row['topic_id']
                    and allowed(row['document'], self.config) and recent(row['document'], self.now)):
                grouped.setdefault(row['topic_id'], []).append(row)
        for topic in topics(self.store):
            rows = unique_members(grouped.get(topic['id'], []))
            if len(rows) < 2 or (topic['kind'] == 'industry' and len(_participants(rows, self.now)) < 2):
                continue
            key = member_key(rows, RULE_VERSION)
            if topic['input_hash'] == key and topic['analysis']:
                continue
            if self.client.calls >= self.client.limit:
                continue
            evidence = [{'id': r['id'], 'title': r['document']['title'], 'published_at': r['document'].get('published_at'),
                         'profile': r['profile'], 'text': source_text(r['document'])[:6000]} for r in rows]
            payload = {'kind': topic['kind'], 'definition': topic['definition'], 'documents': evidence}
            try:
                logging.getLogger('daily_arxiv').info('生成综合分析：%s（%s 份证据）', topic['definition']['title'], len(rows))
                analysis = self.client.ask('analysis_synthesis', payload, 'analysis_synthesis')
                review = self.client.ask('analysis_review', {**payload, 'analysis': analysis}, 'analysis_review')
                if not review['supported']:
                    # One bounded repair uses evidence plus reviewer feedback. The
                    # next reviewer sees only the evidence and revised analysis.
                    analysis = self.client.ask('analysis_synthesis',
                                               {**payload, 'review_feedback': review.get('reason', '')},
                                               'analysis_synthesis')
                    review = self.client.ask('analysis_review', {**payload, 'analysis': analysis}, 'analysis_review')
                if not review['supported']:
                    raise ValueError('分析证据复核未通过：' + str(review.get('reason', '')))
                self.store.execute('UPDATE analysis_topics SET input_hash=?,analysis=?,error=? WHERE id=?',
                                   (key, json.dumps(analysis, ensure_ascii=False), '', topic['id']))
            except Exception as exc:
                self.store.execute('UPDATE analysis_topics SET error=? WHERE id=?', (str(exc), topic['id']))
