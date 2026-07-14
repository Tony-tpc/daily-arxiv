#!/usr/bin/env python3
"""Tests for DOI/URL/title deduplication and cross-source relationships."""

import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.linking.deduplicator import Deduplicator, canonicalize_url, normalize_doi


class DeduplicatorTests(unittest.TestCase):
    def setUp(self):
        self.linker = Deduplicator({})

    def test_normalizes_doi_and_tracking_urls(self):
        self.assertEqual(
            normalize_doi('https://doi.org/10.1234/ABC.5?utm_source=x'),
            '10.1234/abc.5',
        )
        self.assertEqual(
            canonicalize_url('HTTPS://Example.COM:443/path/?utm_source=x&b=2&a=1#top'),
            'https://example.com/path?a=1&b=2',
        )

    def test_deduplicates_by_doi_canonical_url_and_same_type_title(self):
        documents = [
            _document('paper-a', 'paper', 'arXiv', 'Energy agent coordination', doi='10.1234/energy.1'),
            _document('paper-b', 'paper', 'OpenAlex', 'Different discovery title', doi='https://doi.org/10.1234/ENERGY.1'),
            _document('news-a', 'news', '人民网', '虚拟电厂试点进展', url='https://example.cn/news?id=1&utm_source=x'),
            _document('news-b', 'news', '中国新闻网', '另一个转载标题', url='https://EXAMPLE.cn/news?id=1#top'),
            _document('report-a', 'industry_report', '机构甲', '中国虚拟电厂产业发展年度报告'),
            _document('report-b', 'industry_report', '机构乙', '中国虚拟电厂产业发展年度报告！'),
        ]

        result = self.linker.process(documents)

        self.assertEqual(result['input_count'], 6)
        self.assertEqual(result['output_count'], 3)
        self.assertEqual(result['duplicates_removed'], 3)
        self.assertEqual(len(result['duplicate_groups']), 3)
        merged_paper = next(item for item in result['documents'] if item['source_type'] == 'paper')
        self.assertEqual(merged_paper['duplicate_count'], 1)
        self.assertEqual(set(merged_paper['duplicate_sources']), {'arXiv', 'OpenAlex'})
        self.assertTrue(merged_paper['provenance']['metadata']['merged_documents'])

    def test_relates_exactly_the_five_supported_source_pairs(self):
        cases = [
            ('paper', 'policy', 'paper_policy'),
            ('paper', 'news', 'paper_news'),
            ('paper', 'industry_report', 'paper_industry_report'),
            ('policy', 'news', 'policy_news'),
            ('policy', 'industry_report', 'policy_industry_report'),
        ]
        for left_type, right_type, expected in cases:
            with self.subTest(pair=(left_type, right_type)):
                result = self.linker.process([
                    _document('left', left_type, '来源甲', '文档甲', tags=['虚拟电厂']),
                    _document('right', right_type, '来源乙', '文档乙', tags=['虚拟电厂']),
                ])
                self.assertEqual(result['relation_count'], 1)
                self.assertEqual(
                    result['documents'][0]['related_documents'][0]['relationship'], expected
                )

    def test_does_not_link_unsupported_or_only_generic_topics(self):
        unsupported = self.linker.process([
            _document('news', 'news', '媒体', '新闻', tags=['虚拟电厂']),
            _document('report', 'industry_report', '机构', '报告', tags=['虚拟电厂']),
        ])
        generic = self.linker.process([
            _document('paper', 'paper', 'arXiv', '论文', themes=['能源系统']),
            _document('policy', 'policy', '能源局', '政策', themes=['能源系统']),
        ])

        self.assertEqual(unsupported['relation_count'], 0)
        self.assertEqual(generic['relation_count'], 0)

    def test_relations_are_exposed_on_existing_web_cards(self):
        documents = [
            _document('paper', 'paper', 'arXiv', '虚拟电厂论文', tags=['需求响应'], web_card={}),
            _document('policy', 'policy', '国家能源局', '需求响应政策', tags=['需求响应'], web_card={}),
        ]

        result = self.linker.process(documents)

        self.assertEqual(len(result['documents'][0]['web_card']['related_documents']), 1)
        self.assertIn('duplicate_count', result['documents'][0]['web_card'])


def _document(
    document_id,
    source_type,
    source_name,
    title,
    *,
    doi='',
    url='',
    tags=None,
    themes=None,
    web_card=None,
):
    document = {
        'id': document_id,
        'source_type': source_type,
        'source_name': source_name,
        'title': title,
        'doi': doi,
        'url': url or f'https://example.cn/{document_id}',
        'tags': tags or [],
        'themes': themes or [],
        'research_direction': [],
        'entities': [],
        'provenance': {'metadata': {}},
    }
    if web_card is not None:
        document['web_card'] = web_card
    return document


if __name__ == '__main__':
    unittest.main()
