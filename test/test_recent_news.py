"""Network-free regressions for news body recovery, archive cursors and health."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import httpx

from src.sources.rss_adapter import RSSSourceAdapter
from src.sources.recent_news import refresh_recent
from test.test_rss_adapter import RSS_XML

NOW = '2026-07-14T00:00:00+00:00'


class RecentNewsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.feed = {'name': 'News', 'url': 'https://example.com/rss', 'fetch_detail': True,
                     'detail_content_selector': 'article'}
        self.config = {'sources': {'rss': {'feeds': [self.feed], 'max_age_days': 30,
            'state_path': str(Path(self.temp.name) / 'state.json'),
            'snapshot_dir': str(Path(self.temp.name) / 'raw'),
            'recent_backfill': {'enabled': True, 'details_per_run': 2, 'pages_per_feed': 1}}}}
        self.adapter = RSSSourceAdapter(self.config)
        self.adapter.client.close()
        self.adapter.client = Mock()
        self.adapter._now = lambda: NOW

    def response(self, body, code=200):
        return httpx.Response(code, content=body.encode() if isinstance(body, str) else body,
                              request=httpx.Request('GET', 'https://example.com'))

    def test_description_does_not_prevent_full_body_fetch(self):
        self.adapter.client.get.side_effect = [self.response(RSS_XML), self.response('<article>' + 'body ' * 50 + '</article>')]
        records = self.adapter.fetch()
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['detail_fetched'])
        self.assertGreater(len(records[0]['content']), 100)
        self.assertEqual(self.adapter.client.get.call_count, 2)

    def test_failed_body_survives_feed_rotation_and_recovers(self):
        self.adapter.client.get.side_effect = [self.response(RSS_XML), self.response('', 503)]
        self.assertEqual(self.adapter.fetch(), [])
        self.assertEqual(len(self.adapter.state['pending_details']), 1)
        self.assertFalse(self.adapter.state['seen'])
        restored = RSSSourceAdapter(self.config)
        restored.client.close(); restored.client = Mock(); restored._now = lambda: NOW
        restored.client.get.return_value = self.response('<article>' + 'recovered ' * 30 + '</article>')
        records = refresh_recent(restored, [])
        self.assertEqual(len(records), 1)
        self.assertFalse(restored.state['pending_details'])
        self.assertEqual(len(restored.state['seen']), 1)

    def test_stale_feed_stays_stale_on_304(self):
        old = RSS_XML.replace(b'2026', b'2025')
        self.feed['fetch_detail'] = False
        self.adapter.client.get.side_effect = [self.response(old), self.response('', 304)]
        self.adapter.fetch(); self.adapter.fetch()
        state = self.adapter.state['feeds'][self.feed['url']]
        self.assertIn('2025', state['freshness_warning'])
        self.assertEqual(state['last_success_at'], NOW)

    def test_seen_short_document_can_be_enriched_without_changing_publication_date(self):
        raw = self.adapter._raw_entry({'title': 'news', 'link': 'https://example.com/story',
            'published': '2026-07-13', 'summary': 'short'}, self.feed, self.feed['url'], '', NOW)
        doc = self.adapter.normalize([raw])[0]
        self.adapter.state['seen'][raw['dedup_key']] = NOW
        self.adapter.client.get.return_value = self.response('<article>' + 'long body ' * 30 + '</article>')
        records = refresh_recent(self.adapter, [doc])
        self.assertEqual(records[0]['published_at'], '2026-07-13')
        self.assertEqual(self.adapter.normalize(records)[0]['id'], doc['id'])

    def test_archive_cursor_resumes_after_failure_and_budget(self):
        archive = {**self.feed, 'url': 'https://example.com/archive', 'item_selector': 'li',
                   'page_url_template': 'https://example.com/archive/{page}', 'max_pages': 3}
        self.config['sources']['rss']['backfill_feeds'] = [archive]
        page = '<li><a href="/2026/07/13/story">energy news</a>2026-07-13</li>'
        self.adapter.client.get.side_effect = [self.response(page), self.response('<article>' + 'text ' * 30 + '</article>')]
        self.assertEqual(len(refresh_recent(self.adapter, [])), 1)
        state = self.adapter.state['recent_archives'][archive['url']]
        self.assertEqual(state['cursor'], 1)
        self.adapter.client.get.side_effect = [self.response('', 503)]
        refresh_recent(self.adapter, [])
        self.assertEqual(state['cursor'], 1)
        self.assertIn('503', state['error'])
        self.adapter.client.get.side_effect = [self.response('<li><a href="/2025/01/01/old">old</a>2025-01-01</li>')]
        refresh_recent(self.adapter, [])
        self.assertTrue(state['complete'])

    def test_pure_official_statistical_dispatch_credits_original_source(self):
        raw = self.adapter._raw_entry({'title': '电力市场交易电量', 'link': 'https://example.com/story',
            'published': '2026-07-13'}, self.feed, self.feed['url'], '', NOW)
        self.adapter.state['pending_details'] = {raw['dedup_key']: raw}
        self.adapter.client.get.return_value = self.response('<article>据国家能源局消息，交易电量' + '统计数据。' * 30 + '</article>')
        records = refresh_recent(self.adapter, [])
        self.assertEqual(records[0]['origin_owner_id'], 'nea.gov.cn')

    def test_enriched_body_beats_old_summary_with_more_metadata(self):
        from src.linking.deduplicator import Deduplicator
        raw = self.adapter._raw_entry({'title': 'news', 'link': 'https://example.com/story',
            'published': '2026-07-13', 'summary': 'short'}, self.feed, self.feed['url'], '', NOW)
        old = self.adapter.normalize([raw])[0]
        old.update({f'legacy_field_{n}': 'metadata' for n in range(20)})
        new = self.adapter.normalize([{**raw, 'detail_fetched': True, 'content': 'body ' * 50}])[0]
        merged = Deduplicator().process([old, new])['documents'][0]
        self.assertEqual(merged['raw_text'], new['raw_text'])
        self.assertTrue(merged['provenance']['metadata']['detail_fetched'])
        self.assertEqual(merged['id'], old['id'])

    def test_daily_archive_keeps_original_cursor_across_midnight_and_excludes_foreign_section(self):
        archive = {**self.feed, 'url': 'https://example.com/archive', 'item_selector': 'li',
                   'date_url_template': 'https://example.com/%Y/%m%d', 'article_path_prefixes': ['/cj/']}
        self.config['sources']['rss']['backfill_feeds'] = [archive]
        page = '<li><a href="/gj/2026/07/14/foreign">能源 overseas</a>2026-07-14</li><li><a href="/cj/2026/07/14/local">能源国内</a>2026-07-14</li>'
        self.adapter.client.get.side_effect = [self.response(page), self.response('<article>' + 'domestic ' * 30 + '</article>')]
        records = refresh_recent(self.adapter, [])
        self.assertEqual(len(records), 1)
        self.assertIn('/cj/', records[0]['url'])
        self.adapter._now = lambda: '2026-07-15T00:00:00+00:00'
        self.adapter.client.get.side_effect = [self.response(page)]
        refresh_recent(self.adapter, [])
        self.assertEqual(self.adapter.client.get.call_args.args[0], 'https://example.com/2026/0713')

    def test_legacy_validator_requires_full_response_to_initialize_freshness(self):
        self.feed['fetch_detail'] = False
        self.adapter.state['feeds'][self.feed['url']] = {'etag': 'legacy'}
        self.adapter.client.get.return_value = self.response(RSS_XML)
        self.adapter.fetch()
        self.assertNotIn('If-None-Match', self.adapter.client.get.call_args.kwargs['headers'])
        self.assertTrue(self.adapter.state['feeds'][self.feed['url']]['latest_published_at'])

    def test_explicit_reprint_credit_is_preserved_and_unknown_credit_is_not_counted(self):
        from src.sources.observations import attach_observations
        from src.hotspots.ranking import _participants
        from src.hotspots.domain import timestamp
        self.feed['detail_source_selector'] = '#credit'
        raw = self.adapter._raw_entry({'title': '电力市场', 'link': 'https://example.com/story',
            'published': '2026-07-13'}, self.feed, self.feed['url'], '', NOW)
        for name, expected in [('人民日报', 'people.com.cn'), ('未核实机构', '')]:
            self.adapter.state['pending_details'] = {raw['dedup_key']: dict(raw)}
            self.adapter.client.get.return_value = self.response(f'<span id="credit">{name}</span><article>' + '文章正文' * 40 + '</article>')
            records = refresh_recent(self.adapter, [])
            doc = attach_observations(self.adapter.normalize(records)[0], self.config)
            counted = _participants([{'document': doc}], timestamp(NOW))
            self.assertEqual(set(counted), {expected} if expected else set())

    def test_failed_details_rotate_under_shared_request_budget(self):
        for name in ('first', 'second', 'third'):
            raw = self.adapter._raw_entry({'title': name, 'link': 'https://example.com/' + name,
                'published': '2026-07-13'}, self.feed, self.feed['url'], '', NOW)
            self.adapter.state.setdefault('pending_details', {})[raw['dedup_key']] = raw
        body = self.response('<article>' + '文章正文' * 40 + '</article>')
        self.adapter.client.get.side_effect = [self.response('', 503), body]
        self.assertEqual(len(refresh_recent(self.adapter, [])), 1)
        self.assertEqual([r['title'] for r in self.adapter.state['pending_details'].values()], ['third', 'first'])
        self.adapter.client.get.side_effect = [body, body]
        self.assertEqual(len(refresh_recent(self.adapter, [])), 2)
        self.assertFalse(self.adapter.state['pending_details'])

    def test_government_copy_with_wire_credit_keeps_original_institution(self):
        from src.sources.observations import attach_observations
        doc = {'id': 'copy', 'title': '电力安全条例全文', 'source_type': 'policy',
               'url': 'https://www.nea.gov.cn/copy', 'raw_text': '新华社北京9月4日电 电力安全条例全文'}
        doc = attach_observations(doc, {})
        self.assertEqual(doc['provenance']['metadata']['observations'][0]['origin_owner_id'], 'xinhua.cn')
