"""Offline behavioral coverage for bounded editorial processing and both boards."""
import json
import logging
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from src.hotspots.domain import content_key, recent, timestamp
from src.hotspots.editorial import EditorialEngine, CachedClient
from src.hotspots.topics import TopicEngine, SECTION_KEYS, RULE_VERSION, member_key, unique_members, profiles
from src.hotspots.publication import publication, selected_documents
from src.hotspots.ranking import recompute
from src.hotspots.store import HotspotStore
from src.linking.deduplicator import Deduplicator
from src.sources.listing import parse_listing
from src.sources.observations import attach_observations
from src.sources.rss_adapter import RSSSourceAdapter

NOW = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)


def document(id='a', source='one.example', hours=1, kind='news'):
    return {'id': id, 'source_type': kind, 'title': '虚拟电厂参与电力市场新机制',
            'raw_text': (('针对虚拟电厂参与现货电力市场的协调控制机制，发布具体试点规则。' if id.endswith('a') or id == 'a' else '研究多智能体对微电网的自治控制与现货价格变化，分析储能电站的收益机制。') + id) * 10,
            'source_name': source, 'url': f'https://{source}/{id}', 'region': 'CN',
            'published_at': (NOW - timedelta(hours=hours)).isoformat(), 'collected_at': NOW.isoformat(),
            'provenance': {'metadata': {'origin_owner_id': source}},
            'authors_or_orgs': ['Researcher'], 'doi': f'10.1234/{id}' if kind == 'paper' else None}


class FakeLLM:
    model = 'offline-test'

    def __init__(self):
        self.requests = []
        self.relation = 'SAME_OCCURRENCE'
        self.score = 82

    def generate(self, prompt, system_prompt='', max_tokens=None):
        self.requests.append((prompt, system_prompt))
        if '独立评分' in system_prompt:
            return json.dumps({'score': self.score, 'reason': '有明确试点与证据'})
        if '是否属于' in system_prompt:
            return '{"decision":"PASS","reason":"能源系统"}'
        if 'SAME_TOPIC' in system_prompt:
            return '{"relation":"SAME_TOPIC","confidence":0.95}'
        if 'SAME_OCCURRENCE' in system_prompt:
            return json.dumps({'relation': self.relation, 'confidence': 0.95})
        return json.dumps({'summary': '发布虚拟电厂参与市场试点规则。', 'core_viewpoints': ['有明确试点'],
                           'research_relevance': '虚拟电厂市场决策', 'worth_reading': True,
                           'follow_up_suggestions': ['核对试点范围'], 'display_title': '虚拟电厂市场试点规则',
                           'research_topic': '虚拟电厂现货市场协调控制', 'facts': {'subject': '虚拟电厂'}})


class HotspotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = {'hotspots': {'enabled': True, 'state_path': str(Path(self.temp.name) / 'state.sqlite3')},
                       'paper_quality': {'enabled': False}, 'sources': {}}
        # Test corpus papers are already admitted; production uses the unchanged quality gate.
        gate = patch('src.hotspots.domain.is_high_impact_paper', return_value=True)
        gate.start()
        self.addCleanup(gate.stop)
        self.client = FakeLLM()

    def seed(self, docs, group='industry-test'):
        store = HotspotStore(self.config)
        kind = 'academic' if docs[0]['source_type'] == 'paper' else 'industry'
        store.execute('INSERT OR IGNORE INTO analysis_topics (id,kind,definition) VALUES (?,?,?)',
                      (group, kind, json.dumps({'title': '虚拟电厂市场协调控制'})))
        for doc in docs:
            attach_observations(doc, self.config)
            store.save_document(doc, content_key(doc), {'status': 'complete', 'selected': True, 'score': 80}, NOW.isoformat())
            store.execute('INSERT OR REPLACE INTO analysis_profiles VALUES (?,?,?,?,?,?,?,?)',
                          (doc['id'], content_key(doc), 'test', json.dumps(doc), '{}', 'complete', group, ''))
        rows = unique_members([r for r in profiles(store) if r['topic_id'] == group])
        analysis = {'summary': '跨资料综合结论', 'evidence_ids': [r['id'] for r in rows],
                    'sections': [{'key': k, 'title': k, 'text': '有证据的综合分析', 'kind': 'fact',
                                  'evidence_ids': [r['id'] for r in rows]} for k in SECTION_KEYS[kind]]}
        store.execute('UPDATE analysis_topics SET input_hash=?,analysis=? WHERE id=?',
                      (member_key(rows, RULE_VERSION), json.dumps(analysis), group))
        return store

    def test_two_scores_are_independent_and_restart_reuses_results(self):
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([document()])
        scores = [request for request in self.client.requests if '独立评分' in request[1]]
        self.assertEqual(len(scores), 2)
        self.assertEqual(scores[0], scores[1])
        before = len(self.client.requests)
        EditorialEngine(self.config, client=self.client, now=NOW).process([document()])
        self.assertEqual(before, len(self.client.requests))
        self.assertTrue(engine.store.documents()[0]['editorial']['selected'])

    def test_budget_persists_pending_and_resumes_on_empty_input(self):
        self.config['hotspots']['max_calls_per_run'] = 2
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([document()])
        self.assertEqual(engine.client.calls, 2)
        self.assertEqual(engine.store.documents()[0]['editorial']['status'], 'pending')
        self.config['hotspots']['max_calls_per_run'] = 10
        resumed = EditorialEngine(self.config, client=self.client, now=NOW)
        resumed.process([])
        self.assertEqual(resumed.client.calls, 2)  # score two and writing; first two cached
        self.assertEqual(resumed.store.documents()[0]['editorial']['status'], 'complete')

    def test_prompt_change_revisits_completed_documents(self):
        EditorialEngine(self.config, client=self.client, now=NOW).process([document()])
        before = len(self.client.requests)
        original = Path.read_text
        def changed(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text + '\n修订评分标准' if path.name == 'score.md' else text
        with patch.object(Path, 'read_text', changed):
            EditorialEngine(self.config, client=self.client, now=NOW).process([document()])
        self.assertEqual(len(self.client.requests) - before, 2)

    def test_invalid_score_is_not_cached_forever(self):
        self.client.score = 101
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([document()])
        self.assertFalse(engine.store.documents()[0]['editorial']['selected'])
        self.client.score = 80
        EditorialEngine(self.config, client=self.client, now=NOW).process([])
        self.assertEqual(engine.store.documents()[0]['editorial']['status'], 'complete')

    def test_transport_failure_is_pending_not_selected(self):
        self.client.generate = Mock(side_effect=RuntimeError('offline'))
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([document()])
        decision = engine.store.documents()[0]['editorial']
        self.assertEqual(decision['status'], 'pending')
        self.assertFalse(decision['selected'])

    def test_old_and_future_documents_do_not_call_model(self):
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([document(hours=169), document('future', hours=-1)])
        self.assertFalse(self.client.requests)

    def test_window_boundaries_use_original_publication_time(self):
        for kind, days in [('news', 7), ('paper', 180)]:
            with self.subTest(kind=kind):
                self.assertTrue(recent(document(kind=kind, hours=days * 24 - 1), NOW))
                self.assertFalse(recent(document(kind=kind, hours=days * 24), NOW))
                self.assertFalse(recent(document(kind=kind, hours=-1), NOW))

    def test_expanded_windows_are_shared_by_selection_grouping_and_publication(self):
        for kind, days, board in [('news', 6, 'industry'), ('paper', 179, 'academic')]:
            with self.subTest(kind=kind):
                docs = [document(kind + 'a', hours=days * 24, kind=kind),
                        document(kind + 'b', 'two.example', hours=days * 24, kind=kind)]
                engine = EditorialEngine(self.config, client=self.client, now=NOW)
                engine.process(docs)
                recompute(self.config, store=self.seed(docs, board + "-test"), now=NOW)
                self.assertEqual(len(selected_documents(self.config, docs, now=NOW)), 2)
                entries = publication(self.config, docs, now=NOW)['boards'][board]
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]['report_count'], 2)

    def test_hard_exclusions_precede_selection(self):
        doc = document()
        doc['title'] = '人形机器人用于能源机械臂'
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([doc])
        self.assertFalse(self.client.requests)

    def test_independent_owners_and_half_life(self):
        docs = [document('a', hours=24), document('b', source='two.example', hours=0)]
        result = recompute(self.config, store=self.seed(docs), now=NOW)
        entry = result['boards']['industry'][0]
        self.assertEqual(entry['score'], 15)
        self.assertEqual(entry['source_count'], 2)

    def test_same_owner_repeated_articles_do_not_create_hotspot(self):
        docs = [document('a'), document('b')]
        result = recompute(self.config, store=self.seed(docs), now=NOW)
        self.assertEqual(result['boards']['industry'], [])

    def test_canonical_id_replacement_preserves_group_and_does_not_revive_duplicates(self):
        doc = document('old-id')
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([doc])
        group = engine.store.documents()[0]['group_id']
        replacement = {**doc, 'id': 'canonical-id', 'duplicate_document_ids': ['old-id']}
        engine.process([replacement])
        rows = engine.store.documents()
        self.assertEqual([row['id'] for row in rows], ['canonical-id'])
        self.assertEqual(rows[0]['group_id'], group)
        self.assertEqual([item['id'] for item in engine.process([])], ['canonical-id'])

    def test_unselected_documents_never_form_a_hotspot(self):
        self.client.score = 20
        engine = EditorialEngine(self.config, client=self.client, now=NOW)
        engine.process([document('a'), document('b', 'two.example')])
        self.assertTrue(all(row['editorial']['status'] == 'complete' for row in engine.store.documents()))
        self.assertTrue(all(row['group_id'] is None for row in engine.store.documents()))
        self.assertEqual(recompute(self.config, store=engine.store, now=NOW)['boards']['industry'], [])

    def test_dedup_preserves_observations_and_independent_attention(self):
        docs = [attach_observations(document('a'), self.config), attach_observations(document('b', 'two.example'), self.config)]
        merged = Deduplicator().process(docs)['documents']
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]['provenance']['metadata']['observations']), 2)
        result = recompute(self.config, store=self.seed(merged), now=NOW)
        self.assertEqual(result['boards']['industry'], [])  # One deduplicated report is insufficient.

    def test_source_failure_does_not_fabricate_decline(self):
        store = self.seed([document('a'), document('b', 'two.example')])
        store.execute('DELETE FROM sources')
        result = recompute(self.config, store=store, now=NOW)
        entry = result['boards']['industry'][0]
        self.assertEqual(entry['trend'], 'unknown')
        self.assertIsNone(entry['trend_pct'])
        self.assertFalse(entry['coverage']['complete'])

    def test_date_only_is_not_a_new_event(self):
        docs = [document('a'), document('b', 'two.example')]
        for doc in docs:
            doc['published_at'] = '2026-10-02'
        entry = recompute(self.config, store=self.seed(docs), now=NOW)['boards']['industry'][0]
        self.assertFalse(entry['is_new'])
        self.assertEqual(timestamp('2026-10-02').hour, 16)

    def test_different_paper_dois_count_but_database_duplicates_do_not(self):
        docs = [document('a', kind='paper'), document('b', kind='paper'), document('copy', 'crossref', kind='paper')]
        docs[2]['doi'] = docs[0]['doi']
        entry = recompute(self.config, store=self.seed(docs, 'academic-test'), now=NOW)['boards']['academic'][0]
        self.assertEqual(entry['paper_count'], 2)
        self.assertEqual(entry['source_count'], 0)
        self.assertEqual(entry['institution_count'], 0)
        self.assertLessEqual(entry['score'], 2)

    def test_different_policy_numbers_and_dois_survive_title_deduplication(self):
        docs = [document('a', kind='policy'), document('b', kind='policy')]
        docs[0]['policy_number'], docs[1]['policy_number'] = '能源发〔2026〕1号', '能源发〔2026〕2号'
        self.assertEqual(len(Deduplicator().process(docs)['documents']), 2)
        papers = [document('a', kind='paper'), document('b', kind='paper')]
        for item in papers:
            item['authors_or_orgs'] = ['同一作者']
        self.assertEqual(len(Deduplicator().process(papers)['documents']), 2)

    def test_changed_admission_suppresses_cached_entry_and_links_are_audited(self):
        docs = [document('a'), document('b', 'two.example')]
        recompute(self.config, store=self.seed(docs), now=NOW)
        payload = publication(self.config, docs, now=NOW)
        self.assertFalse(payload['details']['industry-test']['evidence'][0]['url'])
        docs[1]['region'] = 'US'
        self.assertEqual(publication(self.config, docs, now=NOW)['boards']['industry'], [])

    def test_reading_missing_store_does_not_create_it(self):
        self.assertFalse(HotspotStore(self.config, readonly=True).latest())
        self.assertFalse(Path(self.config['hotspots']['state_path']).exists())

    def test_hourly_refresh_is_idempotent_and_has_no_model_calls(self):
        store = self.seed([document('a'), document('b', 'two.example')])
        a = recompute(self.config, store=store, now=NOW)
        b = recompute(self.config, store=store, now=NOW)
        self.assertEqual(a['boards'], b['boards'])
        self.assertEqual(len(store.rows('SELECT * FROM snapshots')), 1)

    def test_web_empty_board_validation_and_missing_detail(self):
        from src.web import app as web
        with patch.dict(web.config, self.config), patch.object(web, '_load_intelligence_documents', return_value=[]):
            client = web.app.test_client()
            self.assertEqual(client.get('/api/hotspots').get_json()['entries'], [])
            self.assertEqual(client.get('/api/hotspots').get_json()['window_hours'], 168)
            self.assertEqual(client.get('/api/hotspots?board=academic').get_json()['window_hours'], 4320)
            self.assertEqual(client.get('/api/hotspots?board=invalid').status_code, 400)
            self.assertEqual(client.get('/api/hotspots/missing').status_code, 404)
            self.assertFalse(Path(self.config['hotspots']['state_path']).exists())


class ListingTests(unittest.TestCase):
    def test_incremental_window_skips_old_detail_failures_without_changing_dates(self):
        with tempfile.TemporaryDirectory() as root:
            feed = {'name': '能源', 'url': 'https://energy.example/list', 'format': 'html',
                    'date_selector': 'span', 'max_age_days': 7, 'fetch_detail': True}
            adapter = RSSSourceAdapter({'sources': {'rss': {'feeds': [feed], 'state_path': root + '/state.json', 'snapshot_dir': root + '/raw'}}})
            def response(url, **kwargs):
                text = ('<li><a href="/old">旧能源政策</a><span>2026-09-01</span></li>'
                        '<li><a href="/new">新能源政策</a><span>2026-10-01</span></li>') if url.endswith('/list') else '<article>电力系统管理规则原文</article>'
                return httpx.Response(200, text=text, request=httpx.Request('GET', url))
            adapter.client = Mock(get=Mock(side_effect=response))
            with patch('src.sources.rss_adapter.datetime', wraps=datetime) as clock:
                clock.now.return_value = NOW
                records = adapter.fetch()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['published_at'], '2026-10-01')
            self.assertFalse(any(c.args[0].endswith('/old') for c in adapter.client.get.call_args_list))
            self.assertEqual(adapter.state['feeds'][feed['url']]['last_error'], '')

    def test_failed_detail_is_retried_and_another_source_still_succeeds(self):
        with tempfile.TemporaryDirectory() as root:
            feed = {'name': '能源', 'url': 'https://energy.example/list', 'format': 'html', 'fetch_detail': True}
            second = {'name': '电网', 'url': 'https://grid.example/rss'}
            config = {'sources': {'rss': {'feeds': [feed, second], 'state_path': root + '/state.json', 'snapshot_dir': root + '/raw'}}}
            adapter = RSSSourceAdapter(config)
            def response(url, **kwargs):
                req = httpx.Request('GET', url)
                if url.endswith('/list'):
                    return httpx.Response(200, text='<li><a href="/article">储能政策实施</a></li>', headers={'ETag': 'v1'}, request=req)
                if url.endswith('/article'):
                    return httpx.Response(503, request=req)
                return httpx.Response(200, text='<rss><channel><item><title>电网规划发布</title><link>https://grid.example/item</link></item></channel></rss>', request=req)
            adapter.client = Mock(get=Mock(side_effect=response))
            records = adapter.fetch()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['title'], '电网规划发布')
            self.assertEqual(adapter.state['feeds'][feed['url']]['etag'], '')
            self.assertTrue(adapter.state['feeds'][feed['url']]['last_error'])
            adapter.fetch()
            self.assertEqual(sum(call.args[0].endswith('/article') for call in adapter.client.get.call_args_list), 2)

    def test_html_and_json_share_normalized_fields(self):
        response = httpx.Response(200, text='<ul><li><a href="/a">能源新规</a><span>2026-10-02</span></li></ul>')
        settings = {'url': 'https://energy.example', 'format': 'html', 'date_selector': 'span'}
        entry = parse_listing(response, settings)[0]
        self.assertEqual(entry['link'], 'https://energy.example/a')
        self.assertEqual(entry['published'], '2026-10-02')
        self.assertEqual(parse_listing(httpx.Response(200, json={'items': [{'title': '能源', 'url': '/b', 'published_at': '2026-10-02'}]}),
                                       {'url': 'https://energy.example', 'format': 'json', 'items_path': 'items'})[0]['link'], 'https://energy.example/b')

    def test_empty_html_and_bad_json_are_errors(self):
        with self.assertRaises(ValueError):
            parse_listing(httpx.Response(200, text='<html></html>'), {'url': 'https://example.org'})
        with self.assertRaises(ValueError):
            parse_listing(httpx.Response(200, json={'items': [{'title': '能源'}]}), {'url': 'https://example.org', 'format': 'json', 'items_path': 'items'})

    def test_rss_304_clears_prior_failure_and_records_success(self):
        with tempfile.TemporaryDirectory() as root:
            config = {'sources': {'rss': {'feeds': [{'name': '能源', 'url': 'https://energy.example/rss'}],
                       'state_path': root + '/state.json', 'snapshot_dir': root + '/raw'}}}
            adapter = RSSSourceAdapter(config)
            adapter.state['feeds']['https://energy.example/rss'] = {'last_error': 'offline'}
            adapter.client = Mock(get=Mock(return_value=httpx.Response(304)))
            self.assertEqual(adapter.fetch(), [])
            state = adapter.state['feeds']['https://energy.example/rss']
            self.assertEqual(state['last_error'], '')
            self.assertTrue(state['last_success_at'])


if __name__ == '__main__':
    unittest.main()
