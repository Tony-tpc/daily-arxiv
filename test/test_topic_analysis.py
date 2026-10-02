"""Deterministic synthesis, budget, fixed-boundary and publication regressions."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from test import test_hotspots as fixtures
NOW, document = fixtures.NOW, fixtures.document
from src.hotspots.editorial import CachedClient, EditorialEngine
from src.hotspots.topics import TopicEngine, profiles, topics, SECTION_KEYS
from src.hotspots.publication import publication
from src.hotspots.ranking import recompute
from src.hotspots.store import HotspotStore


class AnalysisModel:
    model = 'offline-analysis'

    def __init__(self):
        self.requests = []
        self.invalid_refs = False
        self.supported = True
        self.disagree = False

    def generate(self, prompt, system_prompt='', max_tokens=None):
        data = json.loads(prompt)
        self.requests.append(data)
        if 'analysis' in data:
            value = {'supported': self.supported, 'reason': '证据审核'}
        elif 'documents' in data:
            ids = [r['id'] for r in data['documents']]
            value = {'summary': '多篇材料支持共同问题，方法有差异，不能直接比较实验数值。',
                     'evidence_ids': ids, 'sections': [
                         {'key': k, 'title': k, 'text': '跨资料综合分析', 'kind': 'inference',
                          'evidence_ids': ['outsider'] if self.invalid_refs else ids}
                         for k in SECTION_KEYS[data['kind']]]}
        elif 'candidates' in data:
            matched = [c for c in data['candidates'] if c['definition']['problem'] == data['profile']['problem']]
            n = sum('candidates' in r for r in self.requests)
            value = {'topic_id': matched[0]['id'] if matched and not (self.disagree and n % 2 == 0) else None,
                     'confidence': .95}
        else:
            problem = '频率控制' if 'frequency' in data['text'] else '价格预测'
            value = {'decision': 'PASS', 'title': problem, 'system': '微电网', 'problem': problem,
                     'definition': '固定问题边界：' + problem,
                     'event': {'identifier': data['id'], 'date': data['published_at']}}
        return json.dumps(value)


class TopicAnalysisTests(unittest.TestCase):
    setUp = fixtures.HotspotTests.setUp
    # Reuse only setup helpers; inherited editorial cases also check coexistence.
    def engine(self, model=None):
        self.model = model or AnalysisModel()
        client = CachedClient(self.config, HotspotStore(self.config), self.model)
        return TopicEngine(self.config, client, now=NOW)

    def papers(self):
        docs = [document('a', kind='paper'), document('b', kind='paper')]
        docs[0]['abstract'] = 'microgrid multi-agent frequency reinforcement-learning ' * 10
        docs[1]['abstract'] = 'microgrid multi-agent frequency model-predictive-control ' * 10
        return docs

    def test_same_problem_different_methods_and_nonselected_papers_publish(self):
        docs = self.papers(); engine = self.engine(); engine.process(docs)
        result = recompute(self.config, now=NOW)
        self.assertEqual(len(result['boards']['academic']), 1)
        entry = result['boards']['academic'][0]
        self.assertEqual(len(entry['analysis']['sections']), 6)
        self.assertEqual(entry['selection_score'], 0)
        rounds = [r for r in self.model.requests if 'candidates' in r]
        self.assertEqual(len(rounds), 2)
        self.assertEqual(rounds[0], rounds[1])
        before = len(self.model.requests)
        self.engine(self.model).process(docs)
        self.assertEqual(before, len(self.model.requests))
        self.assertEqual(recompute(self.config, now=NOW)['boards'], result['boards'])

    def test_same_method_different_problems_and_disagreeing_reviews_stay_separate(self):
        docs = self.papers(); docs[1]['abstract'] = 'microgrid multi-agent price reinforcement-learning ' * 10
        engine = self.engine(); engine.process(docs)
        self.assertEqual(len(topics(engine.store)), 2)
        self.assertEqual(recompute(self.config, now=NOW)['boards']['academic'], [])
        docs = self.papers(); docs[1]['abstract'] += ' changed'
        self.model.disagree = True
        self.engine(self.model).process(docs)
        self.assertEqual(recompute(self.config, now=NOW)['boards']['academic'], [])

    def test_industry_distinct_events_keep_identity_and_same_origin_cannot_publish(self):
        docs = [document('policy-a'), document('policy-b', 'two.example')]
        engine = self.engine(); engine.process(docs)
        result = recompute(self.config, now=NOW)
        entry = result['boards']['industry'][0]
        events = result['details'][entry['id']]['evidence']
        self.assertEqual({e['event']['identifier'] for e in events}, {'policy-a', 'policy-b'})
        for row in profiles(engine.store):
            row['document']['provenance']['metadata']['observations'][0]['origin_owner_id'] = 'same-origin'
            engine.save(row['document'], row['profile'], 'complete', row['topic_id'])
        self.assertEqual(recompute(self.config, now=NOW)['boards']['industry'], [])

    def test_single_and_copied_documents_never_publish(self):
        docs = [document('a'), document('copy', 'two.example')]
        docs[1]['raw_text'] = docs[0]['raw_text']
        self.engine().process(docs)
        self.assertEqual(recompute(self.config, now=NOW)['boards']['industry'], [])

    def test_invalid_citations_retry_and_rejected_review_does_not_publish(self):
        model = AnalysisModel(); model.invalid_refs = True
        engine = self.engine(model); engine.process(self.papers())
        self.assertEqual(recompute(self.config, now=NOW)['boards']['academic'], [])
        self.assertTrue(any(t['error'] for t in topics(engine.store)))
        model.invalid_refs = False
        self.engine(model).process([])
        self.assertEqual(len(recompute(self.config, now=NOW)['boards']['academic']), 1)
        changed = self.papers(); changed[0]['abstract'] += ' updated evidence'
        model.supported = False
        self.engine(model).process(changed)
        self.assertEqual(recompute(self.config, now=NOW)['boards']['academic'], [])

    def test_shared_budget_persists_and_empty_run_resumes(self):
        self.config['hotspots'].update(max_calls_per_run=2, max_documents_per_run=1)
        engine = self.engine(); engine.process(self.papers())
        self.assertEqual(sum(r['status'] == 'pending' for r in profiles(engine.store)), 1)
        editorial = EditorialEngine(self.config, client=self.client, now=NOW)
        editorial.client = engine.client
        self.assertFalse(editorial.client.claim_document('third'))
        self.config['hotspots'].update(max_calls_per_run=300, max_documents_per_run=50)
        self.engine(self.model).process([])
        self.assertEqual(len(recompute(self.config, now=NOW)['boards']['academic']), 1)

    def test_content_change_and_admission_change_hide_published_analysis(self):
        docs = self.papers(); self.engine().process(docs); recompute(self.config, now=NOW)
        self.assertEqual(len(publication(self.config, docs, now=NOW)['boards']['academic']), 1)
        docs[1]['abstract'] += ' corrected'
        self.assertEqual(publication(self.config, docs, now=NOW)['boards']['academic'], [])
        docs[1]['is_retracted'] = True
        self.engine(self.model).process(docs)
        self.assertEqual(len(profiles(HotspotStore(self.config))), 1)

    def test_model_failure_preserves_completed_unchanged_result(self):
        docs = self.papers(); engine = self.engine(); engine.process(docs)
        before = recompute(self.config, now=NOW)['boards']
        with patch.object(self.model, 'generate', side_effect=RuntimeError('offline')):
            self.engine(self.model).process(docs + [document('new', kind='paper')])
        self.assertEqual(recompute(self.config, now=NOW)['boards'], before)

    def test_prompt_upgrade_does_not_prefer_a_singletons_own_paper(self):
        docs = self.papers(); model = AnalysisModel(); model.disagree = True
        engine = self.engine(model); engine.process(docs)
        self.assertEqual(len({r['topic_id'] for r in profiles(engine.store)}), 2)
        model.disagree = False
        original = Path.read_text
        def revised(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            return value + '\n审核修订' if path.name == 'analysis_match.md' else value
        with patch.object(Path, 'read_text', revised):
            self.engine(model).process(docs)
        self.assertEqual(len(recompute(self.config, now=NOW)['boards']['academic']), 1)

    def test_version_refresh_failure_keeps_unchanged_complete_analysis(self):
        docs = self.papers(); engine = self.engine(); engine.process(docs)
        before = recompute(self.config, now=NOW)['boards']
        original = Path.read_text
        def revised(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            return value + '\n审核修订' if path.name == 'analysis_synthesis.md' else value
        with patch.object(Path, 'read_text', revised), patch.object(self.model, 'generate', side_effect=RuntimeError('offline')):
            self.engine(self.model).process(docs)
        self.assertEqual(recompute(self.config, now=NOW)['boards'], before)

    def test_bounded_repair_keeps_second_review_independent(self):
        model = AnalysisModel()
        generate = model.generate
        def reject_once(prompt, **kwargs):
            data = json.loads(prompt)
            if 'analysis' in data:
                model.supported = any('analysis' in r for r in model.requests)
            result = json.loads(generate(prompt, **kwargs))
            if "review_feedback" in data:
                result["summary"] += "已根据原始证据修订。"
            return json.dumps(result)
        model.generate = reject_once
        self.engine(model).process(self.papers())
        reviews = [r for r in model.requests if 'analysis' in r]
        repairs = [r for r in model.requests if 'review_feedback' in r]
        self.assertEqual(len(reviews), 2)
        self.assertEqual(len(repairs), 1)
        self.assertTrue(all('review_feedback' not in r for r in reviews))
        self.assertEqual(len(recompute(self.config, now=NOW)['boards']['academic']), 1)
