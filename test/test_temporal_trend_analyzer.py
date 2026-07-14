"""Tests for historical topic, entity, and source trend analysis."""

import unittest
from unittest.mock import Mock

from src.analyzer.trend_analyzer import TrendAnalyzer


class TemporalTrendAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = TrendAnalyzer.__new__(TrendAnalyzer)
        self.analyzer.config = {
            'analysis': {'trend_window_days': [7, 30, 60]},
        }

    def test_temporal_windows_detect_momentum_decline_and_sources(self):
        observations = [
            _observation('2026-07-01', 'old-1', ['传统调度'], ['国家能源局'], 'policy'),
            _observation('2026-07-05', 'old-2', ['传统调度'], ['电网企业'], 'industry_report'),
            _observation('2026-07-09', 'new-1', ['虚拟电厂'], ['国家能源局'], 'policy'),
            _observation('2026-07-10', 'new-2', ['虚拟电厂'], ['南方电网'], 'news'),
            _observation('2026-07-12', 'new-3', ['虚拟电厂'], ['清华大学'], 'paper'),
            _observation('2026-07-14', 'old-3', ['传统调度'], ['电网企业'], 'paper'),
            _observation(
                '2026-07-14',
                'old-3',
                ['传统调度', '能源智能体'],
                ['电网企业'],
                'paper',
                created_at='2026-07-14T12:00:00Z',
            ),
        ]

        result = self.analyzer.analyze_temporal(observations, as_of='2026-07-14')

        self.assertEqual(result['window_days'], [7, 30, 60])
        self.assertEqual(result['observation_count'], 6)
        self.assertEqual(set(result['windows']), {'7', '30', '60'})
        seven_day = result['windows']['7']
        self.assertEqual(seven_day['current_document_count'], 4)
        self.assertEqual(seven_day['previous_document_count'], 2)
        self.assertIn('虚拟电厂', _names(seven_day['new_topic_emergence']))
        self.assertIn('传统调度', _names(seven_day['topic_decline']))
        self.assertIn('国家能源局', _names(seven_day['entity_frequency_change']))
        self.assertEqual(
            seven_day['cross_source_comparison']['source_counts'],
            {'paper': 2, 'policy': 1, 'news': 1},
        )
        self.assertEqual(result['timeline'][-1]['document_count'], 1)
        self.assertEqual(result['timeline'][-1]['topic_counts']['能源智能体'], 1)

    def test_empty_history_returns_stable_shape(self):
        result = self.analyzer.analyze_temporal([], as_of='2026-07-14')

        self.assertEqual(result['observation_count'], 0)
        self.assertEqual(result['timeline'], [])
        self.assertEqual(result['windows']['7']['topic_momentum'], [])
        self.assertEqual(
            result['windows']['7']['cross_source_comparison']['source_counts'], {}
        )

    def test_invalid_as_of_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid as_of'):
            self.analyzer.analyze_temporal([], as_of='not-a-date')

    def test_mixed_source_documents_use_canonical_fields(self):
        self.analyzer.stop_words = set()
        self.analyzer.logger = Mock()
        self.analyzer.text = lambda zh, en: zh
        documents = [
            {
                'id': 'policy-1',
                'title': '虚拟电厂参与电力调度政策',
                'raw_text': '能源智能体协调需求响应',
                'source_type': 'policy',
                'published_at': '2026-07-14',
                'tags': ['虚拟电厂'],
                'authors_or_orgs': ['国家能源局'],
            },
            {
                'id': 'news-1',
                'title': '虚拟电厂参与需求响应',
                'description': '能源智能体支撑电力调度',
                'source_type': 'news',
                'published_at': '2026-07-13',
                'themes': ['需求响应'],
                'authors_or_orgs': ['中国能源报'],
            },
        ]

        keywords = self.analyzer._extract_keywords(documents, top_n=10)
        topics = self.analyzer._extract_topics(documents, n_topics=2)
        statistics = self.analyzer._generate_statistics(documents)

        self.assertTrue(keywords)
        self.assertEqual(len(topics), 2)
        self.assertEqual(statistics['total_documents'], 2)
        self.assertEqual(statistics['total_authors'], 2)
        self.assertEqual(statistics['category_distribution']['虚拟电厂'], 1)


def _observation(
    snapshot_date,
    document_id,
    topics,
    entities,
    source_type,
    *,
    created_at='2026-07-14T08:00:00Z',
):
    return {
        'snapshot_date': snapshot_date,
        'created_at': created_at,
        'document': {
            'id': document_id,
            'title': document_id,
            'source_type': source_type,
            'research_direction': topics,
            'entities': entities,
        },
    }


def _names(items):
    return {item['name'] for item in items}


if __name__ == '__main__':
    unittest.main()
