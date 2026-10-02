"""Bounded, resumable editorial work using the existing LLM and summary interfaces."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from src.sources.observations import attach_observations, observations
from src.sources.structured_metadata import parse_json_object
from src.summarizer.document_summarizer import DocumentSummarizer
from src.summarizer.llm_factory import LLMClientFactory

from .domain import allowed, content_key, fingerprint, lexical_similarity, recent, strong_identity
from .store import HotspotStore

PROMPTS = Path(__file__).with_name('prompts')


class CallLimitError(RuntimeError):
    pass


class CachedClient:
    """A cache namespace per operation/round prevents the two scores collapsing into one."""
    def __init__(self, config: dict, store: HotspotStore, client=None):
        self.config, self.store, self.client = config, store, client
        self.calls = 0
        self.limit = min(300, max(0, int(config.get('hotspots', {}).get('max_calls_per_run', 300))))
        llm = config.get('llm', {})
        provider = llm.get('provider', 'deepseek')
        settings = llm.get(provider, {})
        self.model = str(getattr(client, 'model', settings.get('model', '')))
        self.route = fingerprint({k: v for k, v in settings.items() if k != 'api_key'}) + str(provider)
        self.namespace = 'writing'

    def generate(self, prompt: str, system_prompt: str = '', max_tokens: int | None = None) -> str:
        key = fingerprint([self.namespace, self.route, self.model, system_prompt, prompt, max_tokens])
        cached = self.store.cached(key)
        if cached is not None:
            return cached
        if self.calls >= self.limit:
            raise CallLimitError('本轮模型调用限额已用完，等待下轮继续')
        if self.client is None:
            self.client = LLMClientFactory.create_client(self.config)
        self.calls += 1
        result = self.client.generate(prompt=prompt, system_prompt=system_prompt, max_tokens=max_tokens)
        # Persist valid structured responses before downstream work; do not cache transport/errors.
        if not isinstance(result, str) or not parse_json_object(result):
            raise ValueError('模型未返回有效 JSON')
        parsed = parse_json_object(result)
        if self.namespace.startswith('score:'):
            score = float(parsed.get('score', -1))
            if not math.isfinite(score) or not 0 <= score <= 100:
                raise ValueError('无效精选分数')
        elif self.namespace == 'prefilter' and parsed.get('decision') not in {'PASS', 'BLOCK', 'UNKNOWN'}:
            raise ValueError('无效预筛结论')
        elif self.namespace.startswith(('topic:', 'relation:')):
            confidence = float(parsed.get('confidence', -1))
            if not math.isfinite(confidence) or not 0 <= confidence <= 1 or parsed.get('relation') not in {'SAME_TOPIC', 'SAME_OCCURRENCE', 'SAME_STORY', 'UNRELATED', 'ROUNDUP'}:
                raise ValueError('无效关系判断')
        elif self.namespace == 'writing':
            DocumentSummarizer._normalize_result(parsed)
        elif self.namespace == 'digest':
            ids = {doc['id'] for doc in json.loads(prompt)['documents']}
            cited = parsed.get('evidence_ids')
            if (not parsed.get('summary') or not isinstance(cited, list)
                    or not all(isinstance(value, str) for value in cited)
                    or len(set(cited)) < 2 or not set(cited) <= ids):
                raise ValueError('无效事件综述或引用标识')
        self.store.execute('INSERT OR REPLACE INTO cache VALUES (?,?)', (key, result))
        return result

    def ask(self, name: str, payload: dict, namespace: str) -> dict:
        self.namespace = namespace
        return parse_json_object(self.generate(json.dumps(payload, ensure_ascii=False),
                                               (PROMPTS / f'{name}.md').read_text(encoding='utf-8'), 1000))


class EditorialEngine:
    def __init__(self, config: dict, *, client=None, now: datetime | None = None):
        self.config = config
        self.now = now or datetime.now(timezone.utc)
        self.store = HotspotStore(config)
        self.client = CachedClient(config, self.store, client)
        from src.summarizer.document_summarizer import SYSTEM_PROMPT
        self.version = fingerprint([SYSTEM_PROMPT, [(p.name, p.read_text(encoding='utf-8')) for p in sorted(PROMPTS.glob('*.md'))],
                                    self.client.route, self.client.model, config.get('hotspots', {}).get('thresholds', {})])

    def process(self, documents: list[dict]) -> list[dict]:
        """Queue only recent admitted documents, then resume a bounded oldest-first batch."""
        indexed = {row['id']: row for row in self.store.documents()}
        for item in documents:
            doc = attach_observations(dict(item), self.config)
            aliases = [str(value) for value in doc.get('duplicate_document_ids', []) if str(value) != doc.get('id')]
            if not doc.get('id') or not allowed(doc, self.config) or not recent(doc, self.now):
                if doc.get('id'):
                    for alias in aliases:
                        self.store.execute('DELETE FROM documents WHERE id=?', (alias,))
                        indexed.pop(alias, None)
                continue
            old = indexed.get(doc['id'])
            digest = content_key(doc)
            if old is None:
                old = next((indexed[key] for key in aliases if key in indexed
                            and (indexed[key]['content_hash'] == digest
                                 or (strong_identity(doc)[1] and strong_identity(doc) == strong_identity(indexed[key]['document'])))), None)
            inherited_group = old['group_id'] if old and old['id'] != doc['id'] else None
            if old and old['content_hash'] == digest and old['editorial'].get('version') == self.version:
                # Refresh source observations without overwriting the completed editorial writing.
                old['document']['id'] = doc['id']
                old['document']['provenance'] = doc['provenance']
                self.store.save_document(old['document'], digest, old['editorial'], old['updated_at'], old['group_id'])
            else:
                self.store.save_document(doc, digest, {'status': 'pending', 'version': self.version,
                                                      'identity_group_id': inherited_group}, self.now.isoformat())
            # Canonical replacements must not revive duplicate members on the next empty run.
            for alias in aliases:
                self.store.execute('DELETE FROM documents WHERE id=?', (alias,))
                indexed.pop(alias, None)
        processed = 0
        maximum = min(50, max(0, int(self.config.get('hotspots', {}).get('max_documents_per_run', 50))))
        for row in self.store.documents():
            doc, decision = row['document'], row['editorial']
            if not allowed(doc, self.config) or not recent(doc, self.now):
                continue
            if decision.get('status') in {'complete', 'blocked', 'awaiting_content'} and decision.get('version') == self.version:
                continue
            if processed >= maximum or self.client.calls >= self.client.limit:
                break
            processed += 1
            decision = {'status': 'pending', 'version': self.version, 'selected': False,
                        'identity_group_id': decision.get('identity_group_id')}
            try:
                material = {key: doc.get(key) for key in ('title', 'source_type', 'published_at', 'source_name')}
                material['text'] = str(doc.get('raw_text') or doc.get('abstract') or doc.get('summary') or '')[:12000]
                prefilter = self.client.ask('prefilter', material, 'prefilter')
                if prefilter.get('decision') not in {'PASS', 'BLOCK', 'UNKNOWN'}:
                    raise ValueError('预筛返回无效 decision')
                decision['prefilter'] = prefilter
                if prefilter['decision'] == 'BLOCK':
                    decision['status'] = 'blocked'
                else:
                    scores = [self.client.ask('score', material, f'score:{round_id}') for round_id in (1, 2)]
                    values = [float(score['score']) for score in scores]
                    if not all(math.isfinite(value) and 0 <= value <= 100 for value in values):
                        raise ValueError('精选分数必须在 0—100 之间')
                    tier = min((obs.get('tier', 'T2') for obs in observations(doc)),
                               key=lambda value: {'T1': 0, 'T1_5': 1, 'T2': 2}.get(value, 2), default='T2')
                    threshold = self.config.get('hotspots', {}).get('thresholds', {}).get(tier, {'T1': 60, 'T1_5': 65, 'T2': 76}.get(tier, 76))
                    decision.update(scores=scores, score=sum(values) / 2, threshold=threshold, tier=tier)
                    self.client.namespace = 'writing'
                    # Keep the original title for identity and auditing; display_title is editorial.
                    doc = DocumentSummarizer(self.config, llm_client=self.client).summarize_document(doc)
                    if doc.get('summary_error'):
                        raise ValueError(doc.get('summary_error_message', '摘要生成失败'))
                    if doc.get('summary_status') in {'missing_abstract', 'insufficient_source_text'}:
                        decision['status'] = 'awaiting_content'
                    else:
                        decision.update(status='complete', selected=sum(values) >= 2 * float(threshold))
                        group_id = (decision.get('identity_group_id') or self.group(doc)) if decision['selected'] else None
                        self.store.save_document(doc, row['content_hash'], decision, self.now.isoformat(), group_id)
                        continue
            except Exception as exc:
                decision.update(status='pending', error=str(exc), selected=False)
            self.store.save_document(doc, row['content_hash'], decision, self.now.isoformat())
        self.write_digests()
        completed = {row['id']: {**row['document'], 'editorial': row['editorial']} for row in self.store.documents()}
        # Include durable pending work on empty collection runs; avoid losing the ordinary library.
        result = {doc['id']: completed.get(doc['id'], doc) for doc in documents}
        result.update({key: doc for key, doc in completed.items() if key not in result and allowed(doc, self.config)})
        return list(result.values())

    def write_digests(self):
        grouped = {}
        for row in self.store.documents():
            if row['group_id'] and row['editorial'].get('status') == 'complete' and row['editorial'].get('selected') and allowed(row['document'], self.config) and recent(row['document'], self.now):
                grouped.setdefault(row['group_id'], []).append(row)
        for group_id, rows in grouped.items():
            if len(rows) < 2 or self.client.calls >= self.client.limit:
                continue
            docs = [{key: row['document'].get(key) for key in ('id', 'title', 'summary', 'published_at')} for row in sorted(rows, key=lambda row: row['id'])]
            digest_key = fingerprint(docs)
            cached = self.store.rows('SELECT input_hash FROM digests WHERE id=?', (group_id,))
            if cached and cached[0]['input_hash'] == digest_key:
                continue
            try:
                result = self.client.ask('digest', {'documents': docs[:10]}, 'digest')
                ids = {doc['id'] for doc in docs[:10]}
                cited = set(result.get('evidence_ids', []))
                if len(cited) < 2 or not cited <= ids:
                    continue
                self.store.execute('INSERT OR REPLACE INTO digests VALUES (?,?,?)', (group_id, digest_key, json.dumps(result, ensure_ascii=False)))
            except Exception:
                # The representative summary remains clearly labelled until the next batch retries.
                continue

    def group(self, doc: dict) -> str:
        academic = doc.get('source_type') == 'paper'
        kind = 'academic' if academic else 'industry'
        text = str(doc.get('title', '')) + ' ' + str(doc.get('summary', ''))[:300]
        candidates = []
        for row in self.store.documents():
            other = row['document']
            if not row['group_id'] or row['id'] == doc['id'] or row['editorial'].get('status') != 'complete':
                continue
            if (other.get('source_type') == 'paper') != academic or not allowed(other, self.config):
                continue
            from .domain import timestamp
            from datetime import timedelta
            at = timestamp(other.get('published_at'))
            if not at or not self.now - timedelta(days=30 if academic else 14) < at <= self.now:
                continue
            left, right = strong_identity(doc), strong_identity(other)
            if not academic and left[1] and left == right:
                return row['group_id']
            similarity = lexical_similarity(text, str(other.get('title', '')) + ' ' + str(other.get('summary', ''))[:300])
            shared = set(doc.get('entities', [])) & set(other.get('entities', []))
            if similarity >= 0.25 or shared:
                candidates.append((similarity, row))
        seen = set()
        for similarity, row in sorted(candidates, key=lambda pair: (-pair[0], pair[1]['id'])):
            if row['group_id'] in seen:
                continue
            seen.add(row['group_id'])
            if len(seen) > 10:
                break
            other = row['document']
            fields = ('title', 'summary', 'published_at', 'source_type', 'doi', 'facts', 'research_topic')
            payload = {'a': {key: doc.get(key) for key in fields}, 'b': {key: other.get(key) for key in fields}}
            name = 'topic' if academic else 'relation'
            verdict = self.client.ask(name, payload, f'{name}:primary')
            acceptable = {'SAME_TOPIC'} if academic else {'SAME_OCCURRENCE', 'SAME_STORY'}
            if verdict.get('relation') not in acceptable or float(verdict.get('confidence', 0)) < 0.8:
                continue
            left, right = strong_identity(doc), strong_identity(other)
            if left[0] == right[0] == 'policy' and left[1] != right[1] and verdict['relation'] == 'SAME_OCCURRENCE':
                continue
            if similarity < 0.85 or float(verdict['confidence']) < 0.9:
                # Review sees only the original evidence, never the first verdict.
                review = self.client.ask(name, payload, f'{name}:review')
                if review.get('relation') != verdict['relation'] or float(review.get('confidence', 0)) < 0.8:
                    continue
            return row['group_id']
        group_id = kind + '-' + fingerprint([kind, doc['id']])[:20]
        topic = doc.get('research_topic')
        title = str(topic if academic and isinstance(topic, str) and topic.strip() else doc.get('display_title') or doc['title'])
        self.store.execute('INSERT OR IGNORE INTO groups VALUES (?,?,?)', (group_id, kind, title))
        return group_id
